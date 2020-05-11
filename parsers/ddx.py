#!/usr/bin/env python3

import os
import sys

from xml.etree.ElementTree import Element, SubElement
from xml.etree import ElementTree as ET
from xml.dom import minidom
from collections import defaultdict
from itertools import chain

DEBUG = False

offset = False  # whether to patch offsets
address = False # whether to patch global addresses

ddtype = dict()	# dictioary of type sizes
ddref = dict() 	# mapping from ELF byte offset to corresponding DIEs' XML nodes
dtree_hashmap = defaultdict(list) # map from location to corr. dd node
dd_subprogram_map = dict() # map from DWARF node to lowest DW_TAG_subprogram ancestor

# these are the clang node tags
Functions = {'FunctionDecl','CXXMethod','CXXConstructor','CXXDestructor'}
Types = {'EnumDecl', 'StructDecl', 'ClassDecl'}
Variables = {'VarDecl', 'FieldDecl', 'ParmDecl'}
All = (Types | Variables | Functions)

# these are the dd node tags
Variable_Container_DIEs = ('DW_TAG_subprogram')
Variable_DIEs = {'DW_TAG_variable', 'DW_TAG_formal_parameter'}


# this function recurses through dd xml to collect all pokemon in dtree
def TraverseDtree(dnode, filetable = [None], parent_die = None):
	
	# get the file table entries from dd. the file table is the child of CU top nodes in dd xml
	if dnode.tag == 'DW_TAG_compile_unit' :
		sources = dnode.find('sources') # the file table entries have tag source
		# the indexing in the table starts from 1, so making first entry as None
		filetable = [None] + [entry.attrib['file'] for entry in sources]

	# Variable_Container_DIEs are the variable container tags we want to keep track of
	# Currently, it is just functions - DW_TAG_subprogram
	if dnode.tag in Variable_Container_DIEs:
		# Since we are processing the dd xml nodes in order (dfs)
		# once we set the parent_die, all recursive calls, going through its descendants,
		# will be passed that node for their parent DIE. 
		# Until a new Variable container is encountered
		parent_die = dnode

	# if we encounter a variable
	if dnode.tag in Variable_DIEs:
		# we set it's parent to the direct function containing it
		# this is needed for templates as you shall see in emit_variable_data
		dd_subprogram_map[dnode] = parent_die

	# this part builds a hashmap out of the dd xml. noting the dd nodes corr to each file location

	# if the node has a well-defined location
	if all('DW_AT_decl_'+x in dnode.attrib for x in ('file', 'line', 'column')):
		# we use that location as the matching criteria (node_hash) for clang
		# this covers everything except enum const, which are not needed anyway
		# here you see why the file table was required
		node_hash = (filetable[ int(dnode.attrib['DW_AT_decl_file']) ],
			int(dnode.attrib['DW_AT_decl_line']), int(dnode.attrib['DW_AT_decl_column']))
		# in case of templates, nodes for each template instantiation have the same location as the template 
		# definition. this is why we need to 'append' the node to the hashmap entry for that file location
		# otherwise, for any file location (ie node_hash), there would be only one node in dd
		dtree_hashmap[node_hash].append(dnode)

	# next we collect the size corresponding to each type in dd xml
	# we may have to go through multiple pointers to get a type's size
	# as type qualifiers (const, volatile, mutable) have pointers to their supertypes, 
	# eg: const volatile unsigned long int -> volatile unsigned long int -> unsigned long int
	# and typedefs have pointers to the type redefined
	# eg: #define A long int; #define B A would lead to B -> A -> long int
	# Note that: pointer types also have links to the type they point to but their size is available directly 
	# at that node itself - the size of pointer is obviously unrelated to the type it points to

	# Anyway, since size (DW_AT_byte_size) is found only at the top supertype
	# Currently, ddtype will only hold sizes for top base types
	# but the magic will happen in try_getting_size_info
	if 'DW_AT_byte_size' in dnode.attrib:
		ddtype[int(dnode.attrib['offset'])] = dnode.attrib['DW_AT_byte_size']

	# map offset to dd node
	# this is required for faster look up of type sizes
	# as the pointers to supertypes are in terms of the DIE offset
	# it is a crucial part of the magic in try_getting_size_info
	if 'offset' in dnode.attrib :
		ddref[int(dnode.attrib['offset'])] = dnode

	# the recursive call, as promised
	for child in dnode:
		TraverseDtree(child, filetable, parent_die)

# this function tries to find the size of any type
# and remember the answer forever in ddtype
# any pointers followed in the quest for the answers are also remembered
# as expected from any good function
def try_getting_size_info(dnode):
	
	# if the size is directly available here, return it
	if 'DW_AT_byte_size' in dnode.attrib :
		return dnode.attrib['DW_AT_byte_size']
	
	# otherwise, there should be a pointer to its supertype
	if 'DW_AT_type' in dnode.attrib:
		# get the supertype offset
		ref_offset = int(dnode.attrib['DW_AT_type'])
		# and this is where ddref comes handy, it takes us directly to the supertype for the recursive call
		ref_dnode = ddref[ref_offset] if ref_offset in ddref else None
		if ref_dnode is not None:
			ret = try_getting_size_info(ref_dnode)
			if ret is not None: return ret
	
	# in cases when a type is declared at one place and define elsewhere
	# two nodes corr to it are generated. one for decl and one for defn
	# the defn node mostly contains address info etc. and it holds a pointer to the decl node
	# as DW_AT_specification. ddref comes handy again when we need to reach this specification node
	if 'DW_AT_specification' in dnode.attrib :
		ref_offset = int(dnode.attrib['DW_AT_specification'])
		ref_dnode = ddref[ ref_offset ] if ref_offset in ddref else None
		if ref_dnode is not None:
			ret = try_getting_size_info(ref_dnode)
			if ret is not None: return ret
	return None

# this function returns the memory location of any dd node
# this could be the offset (address) from the image's load address (DW_OP_addr)
# or, the offset from rbp for local variables (DW_OP_fbreg)
# or, the offset from the object's base address for struct/class member variables (DW_AT_data_member_location)
def try_getting_var_location(dnode) :
	if 'DW_AT_location' in dnode.attrib:
		m = dnode.attrib['DW_AT_location'][1:-1].split()
		if address and 'DW_OP_addr' in m[0]:
			return ('address', str(m[1]))
		# in case of function rbp offsets, the function pushes the return address
		# and the old rbp, before starting execution. so, we need to add 16 (8 bytes each)
		# to get the offset from runtime value of rbp
		elif offset and 'DW_OP_fbreg' in m[0]:
			return ('offset', hex(abs(int(m[1].strip(';')) + 16)))
		return None
	elif 'DW_AT_data_member_location' in dnode.attrib:
		return ('offset', dnode.attrib['DW_AT_data_member_location'])
	return None

# this function finds the memory location from the dnode and patches it in the corr. cnode
def patch_offset(cnode, dnode):
	var_location = try_getting_var_location(dnode)
	if var_location is not None :
		cnode.set(var_location[0], var_location[1])
		return True
	# raise alarm only if you can't find memory address info for non-extern vars
	elif not ('DW_AT_external' in dnode.attrib and 'True' in dnode.attrib['DW_AT_external']) and DEBUG:
		print ('OFFSET NOT FOUND: ', cnode.attrib['usr'], dnode.attrib['offset'])
	# TODO : see also `grep 'DW_AT' pyelftools/elftools/dwarf/enums.py | grep 'location'`
	return False

# this function finds the type size from the dnode and patches it in the corr. cnode
def patch_size(cnode, dnode):
	type_size = try_getting_size_info(dnode)
	if type_size is not None :
		cnode.set('size', type_size)
	elif DEBUG:
		print ('SIZE NOT FOUND: ', cnode.attrib['spelling'], dnode.attrib)

# this function finds the mangled name from the dnode and patches it in the corr. cnode
def patch_mangled(cnode, dnode):
	if 'DW_AT_linkage_name' in dnode.attrib:
		cnode.set('mangled_name', dnode.attrib['DW_AT_linkage_name'])
	elif DEBUG:
		print ('LINKAGE NAME NOT FOUND: ', cnode.attrib['spelling'], dnode.attrib['offset'])

# this function returns a unique dnode matching a cnode location
def get_match(cloc):
	# look for that location in dtree_hashmap
	if cloc in dtree_hashmap:
		match = dtree_hashmap[cloc]
		# if only one dnode is there, we have hit the mark, return it
		# otherwise, we don't know what to do, it must be a template case return none
		if len(match) == 1:
			return match[0]
		elif DEBUG :
			print('MULTIPLE MATCHES: ', cloc, match)
	return None


# Update the static tree generated by ast2xml, with data from the output of
# dwxml. The syntax nodes corresponding to variables, types and functions are updated.
def UpdateCtree (cnode, filename=None, lineno=None, colno=None, outfile=None):

	# If the file / line / col numbers are available for this node, and not for
	# some descendant, remember them for future use, as these are hereditary.
	if 'file' in cnode.attrib:
		filename = os.path.abspath( cnode.attrib['file'] )
	if 'line' in cnode.attrib :
		lineno = int(cnode.attrib['line'])
	if 'col' in cnode.attrib :
		colno = int(cnode.attrib['col'])

	# Filter nodes which we want to update.
	if cnode.tag in All:
		cloc = (filename, lineno, colno)
		if all(cloc) : # None of the three fields are "None"
			match = get_match(cloc) # Returns a matching DWARF node, if unique.
			if match is not None:
				# if DEBUG:
				# 	print ('FOUND ', cloc, cnode.attrib['spelling'], match.attrib['id'])
				if cnode.tag in Variables: # Add offset / address for variables.
					result = patch_offset(cnode, match)
					if result :
						cnode.set('isDef', 'True')
				if cnode.tag in (Variables | Types): # Add size for variables and structs.
					patch_size(cnode, match)
				if cnode.tag in Functions: # Add linkage name for functions.
					patch_mangled(cnode, match)
			elif DEBUG and 'usr' in cnode.attrib:
				print ('MATCH NOT FOUND ', cloc, cnode.tag, cnode.attrib['usr'])

	for child in cnode:
		UpdateCtree(child,filename,lineno,colno)


# generates string representation of given variable node for linkage with PIN later
# var: cnode
# dnode: corr. dnode
# var_class: LOCAL, GLOBAL, STATIC, FUNCSTATIC, STRUCTSTATIC, CLASSSTATIC
# var_container: containing box in case of static variables
def helper(var, dnode = None, var_class = 'LOCAL', var_container = None):
	# STATIC STORAGE VARIABLE:
	# ADDRESS VARNAME ID TYPE SIZE PARENT_ID CLASS CONTAINER

	# AUTO STORAGE VARIABLE:
	# FILENAME FUNCTION OFFSET VARNAME ID TYPE SIZE PARENT_ID   
	s = ''
	if var_class == 'LOCAL':
		# in case of local, find parent name from dnode
		parnode = dd_subprogram_map[ dnode ] if dnode in dd_subprogram_map else None
		if parnode is None : return s
		if 'DW_AT_linkage_name' in parnode.attrib :
			funcname = parnode.attrib['DW_AT_linkage_name']
		elif 'DW_AT_specification' in parnode.attrib :
			snode = ddref[ int(parnode.attrib['DW_AT_specification']) ]
			if 'DW_AT_linkage_name' in snode.attrib :
				funcname = snode.attrib['DW_AT_linkage_name']
			elif 'DW_AT_name' in snode.attrib :
				funcname = snode.attrib['DW_AT_name']
		elif 'DW_AT_name' in parnode.attrib :
			funcname = parnode.attrib['DW_AT_name']

		loc_info = try_getting_var_location(dnode)
		if loc_info is not None and offset and loc_info[0] == 'offset' :
			var_location = loc_info[1]

		s += var.attrib['file'] + '\t'
		s += funcname + '\t'
		s += var_location + '\t'
	
	else:
		addr = '-1'
		if 'address' in var.attrib:
			addr = var.attrib['address']
		s = addr + '\t'

	var_size = '0'
	if dnode is not None:
		var_name = dnode.attrib['DW_AT_name']
		var_size = try_getting_size_info(dnode)
	else:
		var_name = (var.attrib['mangled_name'] if ('mangled_name' in var.attrib) else var.attrib['spelling'])
		if 'size' in var.attrib :
			var_size = var.attrib['size']

	s += var_name + '\t'
	s += var.attrib['id'] + '\t'
	s += var.attrib['type'] + '\t'
	s += var_size + '\t'

	if 'sem_parent_id' in var.attrib:
		s += var.attrib['sem_parent_id'] + '\t'
	elif 'lex_parent_id' in var.attrib:
		s += var.attrib['lex_parent_id'] + '\t'
	else:
		s += 'None' + '\t'

	if var_class != 'LOCAL':
		s += var_class
		if var_container is not None:
			s += '\t' + var_container

	if DEBUG:
		print (s)
	s += '\n'
	return s


def generate_var(croot, outemits_filename, mainexe = False):
	with open(outemits_filename, 'w') as f:
		if address:
			# writing globals
			# ADDRESS VARNAME ID TYPE SIZE PARENT_ID CLASS CONTAINER
			f.write('# ADDRESS\tVARNAME\tVARID\tVARTYPE\tVARSIZE\tPARENTID\tVARCLASS\t[VARCONTAINER]\n')
			
			# Mention any address only once
			printed = set()	
			
			# Static storage variables inside containers
			VARCONTAINERS = dict()
			for func in Functions:
				VARCONTAINERS[func] = 'FUNCSTATIC'
			for ty in Types:
				typename = ty[:ty.lower().rfind('decl')].upper()
				VARCONTAINERS[ty] = typename+'STATIC'
			for nodetype, store in VARCONTAINERS.items():
				# Get all static variables inside
				s = ''
				for obj in croot.findall('.//'+nodetype):
					if 'spelling' in obj.attrib:
						obj_name = (obj.attrib['mangled_name'] if ('mangled_name' \
											in obj.attrib) else obj.attrib['spelling'])
						if DEBUG:
							print (obj_name)
						gen = obj.findall('.//*[@address]')
						if mainexe:
							gen = chain(gen, obj.findall('.//VarDecl[@linkage_kind="external"]'))
						for var in gen:
							if 'offset' in var.attrib:
								continue
							var_name = var.attrib['spelling']
							if 'address' in var.attrib:
								var_name = var.attrib['address']
							elif 'mangled_name' in var.attrib:
								var_name = var.attrib['mangled_name']
							if var_name not in printed:
								printed.add(var_name)
								if DEBUG:
									print (var_name)
								s += helper(var, var_class = store, var_container = obj_name)
				f.write(s)

			# Now out all global variables
			s = ''
			gen = croot.findall('.//*[@address]')
			if mainexe:
				gen = chain(gen, croot.findall('.//VarDecl[@linkage_kind="external"]'))
			for var in gen:
				if 'offset' in var.attrib:
					continue
				var_name = var.attrib['spelling']
				if 'address' in var.attrib:
					var_name = var.attrib['address']
				elif 'mangled_name' in var.attrib:
					var_name = var.attrib['mangled_name']
				if var_name not in printed:
					printed.add(var_name)
					if DEBUG:
						print (var_name)
					if 'storage_class' in var.attrib and var.attrib['storage_class'] == 'STATIC':
						s += helper(var, var_class = 'STATIC')
					else:
						s += helper(var, var_class = 'GLOBAL')
			f.write(s)

		if offset:
			# For all local variable declarations
			# FUNCTION OFFSET VARNAME ID TYPE SIZE PARENT_ID
			f.write('# FILENAME\tFUNCTION\tOFFSET\tVARNAME\tVARID\tVARTYPE\tVARSIZE\tPARENTID\n')

			genfun = chain.from_iterable([croot.findall('.//'+x) for x in Functions])
			for func in genfun:
				s = ''
				if 'spelling' in func.attrib:
					genvar = chain.from_iterable([func.findall('.//'x) for x in Variables])
					for cnode in genvar:
						if 'file' in cnode.attrib:
							filename = os.path.abspath( cnode.attrib['file'] )
						if 'line' in cnode.attrib:
							lineno = int(cnode.attrib['line'])
						if 'col' in cnode.attrib:
							colno = int(cnode.attrib['col'])
						cloc = (filename, lineno, colno)
						if all(cloc) and cloc in dtree_hashmap:
							for match in dtree_hashmap[cloc]:
								s += helper(cnode, match)


				elif DEBUG:
					print(f'{sys.argv[0]} Warning : No spelling for {func.attrib["usr"]}',file=sys.stderr)

				if(len(s) > 0):
					f.write(s)


# This function merges the IDs of definition IDs having the same USR
# across translation units. USR (Unified symbol resolution) is a unique string
# provided by libclang for all program symbols. Symbols having the same USR
# will be linked, and will have the same memory location.
# The order of TUs should be the same as the one given to the linker.
# Since libraries might contain multiple compilation units
# whose symbol resolution order is given here :
# https://eli.thegreenplace.net/2013/07/09/library-order-in-static-linking 
# the order of "picking up" compilation units from them should determine the order
# of patching symbol reference information in respective translation units
# and hence the order in which we pass arguments to this function.
def patch_external_def_ids(rootlist):

	patched_xml = ET.Element('elf')
	
	exported_symbols = dict() # Maps USR to one of the IDs in some translation unit.
	requested_symbols = defaultdict(list) # Symbols needed but not provided by any object so far.

	for root_node in rootlist:

		patched_xml.append(root_node)

		for node in root_node.iter() :
			if 'usr' in node.attrib and 'isDecl' in node.attrib and node.attrib['isDecl'] == 'True':
				if 'isDef' in node.attrib and node.attrib['isDef'] == 'True':
					# overridden symbols for multiple so linking
					if DEBUG:
						print ('x', node.attrib['id'], node.attrib['usr'])

					# We found a new symbol, update our set of exported symbols.
					if node.attrib['usr'] not in exported_symbols:
						exported_symbols[node.attrib['usr']] = node.attrib['id']

					# Update the pointers of all nodes who point to this definition.
					if node.attrib['usr'] in requested_symbols:
						for request in requested_symbols[node.attrib['usr']]:
							request.attrib['def_id'] = node.attrib['id']
						# we are done for these nodes
						requested_symbols.pop(node.attrib['usr'])

				# Declaration that is not a definition.
				else: 
					# If this symbol has already been defined, update the pointer.
					if node.attrib['usr'] in exported_symbols:
						node.attrib['def_id'] = exported_symbols[node.attrib['usr']]
						if DEBUG:
							print ('y', node.attrib['id'], node.attrib['usr'])
					# Otherwise, this def_id pointer will be updated later.
					else:
						requested_symbols[node.attrib['usr']].append(node)
						if DEBUG:
							print (node.attrib['id'], node.attrib['usr'])

	return patched_xml

if __name__ == '__main__':
	fstrip = sys.argv[1]
	if sys.argv[2] == 'OFFSET':
		offset = True
	elif sys.argv[2] == 'ADDRESS':
		address = True

	dwarfxml_filename = fstrip + sys.argv[3]
	clangxml_filename = fstrip + sys.argv[4]
	combined_filename = fstrip + sys.argv[5]
	outemits_filename = fstrip + sys.argv[6]

	dtree = ET.parse(dwarfxml_filename)
	droot = dtree.getroot()

	ctree = ET.parse(clangxml_filename)
	croot = ctree.getroot()

	# create the dtree fast search structures
	TraverseDtree(droot)
	# update the ctree with that information
	UpdateCtree(croot)

	# write out updated xml
	ctree.write(combined_filename, encoding='utf-8')

	# write out the corr. address/offset file
	generate_var(croot, outemits_filename)
	
