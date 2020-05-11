#!/usr/bin/env python3

import os
import sys

from xml.etree.ElementTree import Element, SubElement
from xml.etree import ElementTree as ET
from xml.dom import minidom
from collections import defaultdict

DEBUG = False

offset = False  # whether to patch offsets
address = False # whether to patch global addresses
fstrip = sys.argv[1]
if sys.argv[2] == 'OFFSET':
	offset = True
elif sys.argv[2] == 'ADDRESS':
	address = True

dwarfxml_filename = fstrip + sys.argv[3]
clangxml_filename = fstrip + sys.argv[4]
combined_filename = fstrip + sys.argv[5]
outemits_filename = fstrip + sys.argv[6]
outemits_file = None

dtree = ET.parse(dwarfxml_filename)
droot = dtree.getroot()

ctree = ET.parse(clangxml_filename)
croot = ctree.getroot()

ddtype = dict()	# dictioary of type sizes
ddref = dict() 	# mapping from ELF byte offset to corresponding DIEs' XML nodes
dtree_hashmap = defaultdict(list)

dd_subprogram_map = dict() # map from DWARF node to lowest DW_TAG_subprogram ancestor

Functions = {'FunctionDecl','CXXMethod','CXXConstructor','CXXDestructor'}
Types = {'EnumDecl', 'StructDecl', 'ClassDecl'}
Variables = {'VarDecl', 'FieldDecl', 'ParmDecl'}
Variable_Container_DIEs = ('DW_TAG_subprogram')
Variable_DIEs = {'DW_TAG_variable', 'DW_TAG_formal_parameter'}
All = (Types | Variables | Functions)

def TraverseDtree(dnode, filetable = [None], parent_die = None): # collect all pokemon in dtree
	if 'offset' in dnode.attrib :
		ddref[int(dnode.attrib['offset'])] = dnode
	if dnode.tag == 'DW_TAG_compile_unit' :
		sources = dnode.find('sources')
		filetable = [None] + [entry.attrib['file'] for entry in sources]
	if dnode.tag in Variable_Container_DIEs :
		parent_die = dnode
	if dnode.tag in Variable_DIEs :
		dd_subprogram_map[ dnode ] = parent_die
	if all('DW_AT_decl_'+x in dnode.attrib for x in ('file', 'line', 'column')):
		# covers everything except enum const, which are not needed anyway
		node_hash = (filetable[ int(dnode.attrib['DW_AT_decl_file']) ],
			int(dnode.attrib['DW_AT_decl_line']), int(dnode.attrib['DW_AT_decl_column']))
		# if DEBUG : print(node_hash)
		dtree_hashmap[node_hash].append(dnode)
	if 'DW_AT_byte_size' in dnode.attrib:
		ddtype[int(dnode.attrib['offset'])] = dnode.attrib['DW_AT_byte_size']
	for child in dnode:
		TraverseDtree(child, filetable, parent_die)

def try_getting_size_info(dnode) :
	if 'DW_AT_byte_size' in dnode.attrib :
		return dnode.attrib['DW_AT_byte_size']
	if 'DW_AT_type' in dnode.attrib :
		ref_offset = int(dnode.attrib['DW_AT_type'])
		ref_dnode = ddref[ ref_offset ] if ref_offset in ddref else None
		if ref_dnode is not None :
			ret = try_getting_size_info(ref_dnode)
			if ret is not None : return ret
	if 'DW_AT_specification' in dnode.attrib :
		ref_offset = int(dnode.attrib['DW_AT_specification'])
		ref_dnode = ddref[ ref_offset ] if ref_offset in ddref else None
		if ref_dnode is not None :
			ret = try_getting_size_info(ref_dnode)
			if ret is not None : return ret
	return None

def try_getting_var_location(dnode) :
	if 'DW_AT_location' in dnode.attrib:
		m = dnode.attrib['DW_AT_location'][1:-1].split()
		if address and 'DW_OP_addr' in m[0]:
			return ('address', str(m[1]))
		elif offset and 'DW_OP_fbreg' in m[0]:
			return ('offset', hex(abs(int(m[1].strip(';')) + 16)))
		return None
	elif 'DW_AT_data_member_location' in dnode.attrib:
		return ('offset', dnode.attrib['DW_AT_data_member_location'])
	return None

def patch_offset(cnode, dnode):
	var_location = try_getting_var_location(dnode)
	if var_location is not None :
		cnode.set(var_location[0], var_location[1])
		return True
	elif not ('DW_AT_external' in dnode.attrib and 'True' in dnode.attrib['DW_AT_external']) and DEBUG:
		print ('OFFSET NOT FOUND: ', cnode.attrib['usr'], dnode.attrib['offset'])
	# TODO : see also `grep 'DW_AT' pyelftools/elftools/dwarf/enums.py | grep 'location'`
	return False

def patch_size(cnode, dnode):
	type_size = try_getting_size_info(dnode)
	if type_size is not None :
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


def UpdateCtree (cnode, filename=None, lineno=None, colno=None):
	if 'file' in cnode.attrib:
		filename = os.path.abspath( cnode.attrib['file'] )
	if 'line' in cnode.attrib :
		lineno = int(cnode.attrib['line'])
	if 'col' in cnode.attrib :
		colno = int(cnode.attrib['col'])

	if cnode.tag in All:
		cloc = (filename, lineno, colno)
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

	if cnode.tag in Variables and all(cloc) :
		if cloc in dtree_hashmap :
			for match in dtree_hashmap[cloc] :
				emit_variable_data(filename, cnode, match)

	for child in cnode:
		UpdateCtree(child,filename,lineno,colno)


def emit_variable_data(filename, cnode, dnode) :
	parnode = dd_subprogram_map[ dnode ] if dnode in dd_subprogram_map else None
	if parnode is None : return

	funcname, var_location, var_name, var_type, \
		type_size, par_id = None, None, None, None, None, None

	if "DW_AT_linkage_name" in parnode.attrib :
		funcname = parnode.attrib["DW_AT_linkage_name"]
	elif "DW_AT_specification" in parnode.attrib :
		snode = ddref[ int(parnode.attrib["DW_AT_specification"]) ]
		if "DW_AT_linkage_name" in snode.attrib :
			funcname = snode.attrib["DW_AT_linkage_name"]
		elif "DW_AT_name" in snode.attrib :
			funcname = snode.attrib["DW_AT_name"]
	elif "DW_AT_name" in parnode.attrib :
		funcname = parnode.attrib["DW_AT_name"]

	loc_info = try_getting_var_location(dnode)
	if loc_info is not None and offset and loc_info[0] == 'offset' :
		var_location = loc_info[1]
	else:
		return
	# if loc_info is not None and address and loc_info[0] == 'address' :
	# 	var_location = loc_info[1]

	if "DW_AT_name" in dnode.attrib :
		var_name = dnode.attrib["DW_AT_name"]

	var_type = cnode.attrib["type"] if "type" in cnode.attrib else None
	type_size = try_getting_size_info(dnode)
	var_id = cnode.attrib["id"] if "id" in cnode.attrib else None

	par_id = (cnode.attrib["sem_parent_id"] if "sem_parent_id" in cnode.attrib else None)
	if par_id is None :
		par_id = (cnode.attrib["lex_parent_id"] if "lex_parent_id" in cnode.attrib else None)

	print(filename, funcname, var_location, var_name,
		var_id, var_type, type_size, par_id, sep='\t', file=outemits_file)

TraverseDtree(droot)

with open(outemits_filename, 'w') as outemits_file :
	print('# FILENAME\tFUNCTION\tOFFSET\tVARNAME\tVARID\tVARTYPE\tVARSIZE\tPARENTID', file=outemits_file)
	UpdateCtree(croot)

# write out updated xml
ctree.write(combined_filename, encoding="utf-8")
