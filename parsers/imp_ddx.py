#!/usr/bin/env python3

import os
import sys

from xml.etree.ElementTree import Element, SubElement
from xml.etree import ElementTree as ET
from xml.dom import minidom
from collections import defaultdict
from itertools import chain

DEBUG = False

ddtype = dict()	# dictioary of type sizes
ddref = dict() 	# mapping from ELF byte offset to corresponding DIEs' XML nodes
dtree_hashmap = defaultdict(list)
offset = False  # whether to patch offsets
address = False # whether to patch global addresses


Functions = {'FunctionDecl','CXXMethod','CXXConstructor','CXXDestructor'}
Types = {'EnumDecl', 'StructDecl', 'ClassDecl'}
Variables = {'VarDecl', 'FieldDecl', 'ParmDecl'}
All = (Types | Variables | Functions)

def TraverseDtree(dnode, filetable): # collect all pokemon in dtree
	if 'offset' in dnode.attrib :
		ddref[int(dnode.attrib['offset'])] = dnode
	if dnode.tag == 'DW_TAG_compile_unit' :
		sources = dnode.find('sources')
		filetable = [None] + [entry.attrib['file'] for entry in sources]
	if all('DW_AT_decl_'+x in dnode.attrib for x in ('file', 'line', 'column')):
		# covers everything except enum const, which are not needed anyway
		node_hash = (filetable[int(dnode.attrib['DW_AT_decl_file']) ],
			int(dnode.attrib['DW_AT_decl_line']), int(dnode.attrib['DW_AT_decl_column']))
		# if DEBUG : print(node_hash)
		dtree_hashmap[node_hash].append(dnode)
	if 'DW_AT_byte_size' in dnode.attrib:
		ddtype[int(dnode.attrib['offset'])] = dnode.attrib['DW_AT_byte_size']
	for child in dnode:
		TraverseDtree(child, filetable)

def try_getting_size_info(dnode) :
	if 'DW_AT_byte_size' in dnode.attrib :
		return dnode.attrib['DW_AT_byte_size']
	if 'DW_AT_type' in dnode.attrib :
		ref_offset = int(dnode.attrib['DW_AT_type'])
		ref_dnode = ddref[ ref_offset ] if ref_offset in ddref else None
		if ref_dnode is not None :
			ret = try_getting_size_info(ref_dnode)
			if ret != -1 : return ret
	if 'DW_AT_specification' in dnode.attrib :
		ref_offset = int(dnode.attrib['DW_AT_specification'])
		ref_dnode = ddref[ ref_offset ] if ref_offset in ddref else None
		if ref_dnode is not None :
			ret = try_getting_size_info(ref_dnode)
			if ret != -1 : return ret
	return -1

def patch_offset(cnode, dnode):
	if 'DW_AT_location' in dnode.attrib:
		m = dnode.attrib['DW_AT_location'][1:-1].split()
		if address and 'DW_OP_addr' in m[0]:
			cnode.set('address', '0x'+m[1])
		elif offset and 'DW_OP_fbreg' in m[0]:
			cnode.set('offset', hex(abs(int(m[1]) + 16)))
		return True
	elif 'DW_AT_data_member_location' in dnode.attrib:
		cnode.set('offset', dnode.attrib['DW_AT_data_member_location'])
		return dnode
	elif DEBUG:
		print ('OFFSET NOT FOUND: ', cnode.attrib['usr'], dnode.attrib['offset'], dnode.attrib)
	# TODO : see also `grep 'DW_AT' pyelftools/elftools/dwarf/enums.py | grep 'location'`
	return None

def patch_size(cnode, dnode):
	type_size = try_getting_size_info(dnode)
	if type_size != -1 :
		cnode.set('size', type_size)
	elif DEBUG:
		print ('SIZE NOT FOUND: ', cnode.attrib['spelling'], dnode.attrib)

def patch_mangled(cnode, dnode):
	if 'DW_AT_linkage_name' in dnode.attrib:
		cnode.set('mangled_name', dnode.attrib['DW_AT_linkage_name'])
	elif DEBUG:
		print ('LINKAGE NAME NOT FOUND: ', cnode.attrib['spelling'], dnode.attrib['offset'])

def get_match(cloc):
	if cloc in dtree_hashmap:
		match = dtree_hashmap[cloc]
		if len(match) == 1:
			return match[0]
		elif DEBUG :
			print('MULTIPLE MATCHES:', cloc, match)
	return None

def try_patching_node(cloc, cnode) :
	if cnode.tag in All :
		if all(cloc) :
			match = get_match(cloc)
			if match is not None:
				# if DEBUG:
				# 	print ('FOUND ', cloc, cnode.attrib['spelling'], match.attrib['id'])
				if cnode.tag in Variables:
					result = patch_offset(cnode, match)
					if result :
						cnode.set('isDef', 'True')
				if cnode.tag in (Variables | Types):
					patch_size(cnode, match)
				if cnode.tag in Functions:
					patch_mangled(cnode, match)
			elif DEBUG and 'usr' in cnode.attrib:
				print ('MATCH NOT FOUND ', cloc, cnode.tag, cnode.attrib['usr'])

def UpdateCtree (cnode, filename=None, lineno=None, colno=None, parent_node = None):
	if 'file' in cnode.attrib:
		filename = os.path.abspath( cnode.attrib['file'] )
	if 'line' in cnode.attrib :
		lineno = int(cnode.attrib['line'])
	if 'col' in cnode.attrib :
		colno = int(cnode.attrib['col'])
	cloc = (filename, lineno, colno)
	# done for scope resolution fix
	if parent_node is not None and parent_node.tag in Variables :
		try_patching_node(cloc, parent_node)
	for child in cnode:
		UpdateCtree(child,filename,lineno,colno,cnode)
	try_patching_node(cloc, cnode)

# generates string representation of given variable node for linkage with PIN later
def helper(var, var_class, var_container = None):
	# STATIC STORAGE VARIABLE:
	# ADDRESS VARNAME ID TYPE SIZE PARENT_ID CLASS CONTAINER

	# AUTO STORAGE VARIABLE:
	# FILENAME FUNCTION OFFSET VARNAME ID TYPE SIZE PARENT_ID   
	s = ''
	if var_class == 'LOCAL':
		s += var.attrib['file'] + '\t'
		s += var_container + '\t'
		s += var.attrib['offset'] + '\t'
	else:
		addr = '-1'
		if 'address' in var.attrib:
			addr = var.attrib['address']
		s = addr + '\t'

	var_name = (var.attrib['mangled_name'] if ('mangled_name' in var.attrib) else var.attrib['spelling'])
	s += var_name + '\t'
	s += var.attrib['id'] + '\t'
	s += var.attrib['type'] + '\t'
	var_size = '0'
	if 'size' in var.attrib :
		var_size = var.attrib['size']
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
								s += helper(var, store, obj_name)
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
						s += helper(var, 'STATIC')
					else:
						s += helper(var, 'GLOBAL')
			f.write(s)

		if offset:
			# For all local variable declarations
			# FUNCTION OFFSET VARNAME ID TYPE SIZE PARENT_ID
			f.write('# FILENAME\tFUNCTION\tOFFSET\tVARNAME\tVARID\tVARTYPE\tVARSIZE\tPARENTID\n')

			for nodetype in Functions:
				s = ''
				for func in croot.findall('.//'+nodetype):
					if 'spelling' in func.attrib:
						func_name = func.attrib['spelling']
						if 'mangled_name' in func.attrib:
							func_name = func.attrib['mangled_name']
						for var in func.findall('.//*[@offset]'):
							if var.tag in Variables:
								s += helper(var, 'LOCAL', func_name)
					elif DEBUG:
						print(f'{sys.argv[0]} Warning : No spelling for {func.attrib["usr"]}',file=sys.stderr)
				if(len(s) > 0):
					f.write(s)
	# Offset

def patch_external_def_ids(rootlist):
	patched_xml = ET.Element('elf')

	exported_symbols = dict() # Map USR -> ID
	requested_symbols = defaultdict(list)

	for root_node in rootlist:

		patched_xml.append(root_node)

		for node in root_node.iter() :
			if 'usr' in node.attrib and 'isDecl' in node.attrib and node.attrib['isDecl'] == 'True':
				if 'isDef' in node.attrib and node.attrib['isDef'] == 'True':
					# overridden symbols for multiple so linking
					if DEBUG:
						print ('x', node.attrib['id'], node.attrib['usr'])
					if node.attrib['usr'] not in exported_symbols:
						exported_symbols[node.attrib['usr']] = node.attrib['id']

					# found a guy, patch for all waiting nodes
					if node.attrib['usr'] in requested_symbols:
						for request in requested_symbols[node.attrib['usr']]:
							request.attrib['def_id'] = node.attrib['id']
						# we are done for these nodes
						requested_symbols.pop(node.attrib['usr'])

				# Declaration that is not a definition.
				else: 
					# we know about this guy
					if node.attrib['usr'] in exported_symbols:
						node.attrib['def_id'] = exported_symbols[node.attrib['usr']]
						if DEBUG:
							print ('y', node.attrib['id'], node.attrib['usr'])
					# this guy will have to wait
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

	TraverseDtree(droot, [None])
	UpdateCtree(croot)

	# write out updated xml
	xmlstr = minidom.parseString(ET.tostring(croot)).toprettyxml(indent='   ')
	with open(combined_filename, 'w') as f:
		f.write(xmlstr)

	# write out updated address/offset file
	generate_var(croot, outemits_filename)
