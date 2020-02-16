#!/usr/bin/env python

import os
import sys

from xml.etree.ElementTree import Element, SubElement
from xml.etree import ElementTree as ET
from xml.dom import minidom
from collections import defaultdict

DEBUG = True

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
# outemits_filename = fstrip + sys.argv[6]

dtree = ET.parse(dwarfxml_filename)
droot = dtree.getroot()

ctree = ET.parse(clangxml_filename)
croot = ctree.getroot()

ddtype = dict()	# dictioary of type sizes
ddref = dict() 	# mapping from ELF byte offset to corresponding DIEs' XML nodes
dtree_hashmap = defaultdict(list)

# def collect_types(droot):
# 	for types in droot.findall(".//*[@byte_size]"):
# 		ddtype[types.attrib['id']] = types.attrib['byte_size']

# def show():
# 	for k, v in ddtype.items():
# 		print (k, v)

# collect_types(droot)
# if DEBUG:
# 	show()

Functions = {'FunctionDecl','CXXMethod','CXXConstructor','CXXDestructor'}
Types = {'EnumDecl', 'StructDecl', 'ClassDecl'}
Variables = {'VarDecl', 'FieldDecl', 'ParmDecl'}
All = (Types | Variables | Functions)

def TraverseDtree(dnode, filetable): # collect all pokemon in dtree
	if 'offset' in dnode.attrib :
		ddref[int(dnode.attrib['offset'])] = dnode
	if dnode.tag == "DW_TAG_compile_unit" :
		sources = dnode.find("sources")
		filetable = [None] + [entry.attrib["file"] for entry in sources]
	if all("DW_AT_decl_"+x in dnode.attrib for x in ('file', 'line', 'column')):
# covers everything except enum const, which are not needed anyway
		# if DEBUG : print(dnode, dnode.attrib)
		node_hash = (filetable[ int(dnode.attrib['DW_AT_decl_file']) ],
			int(dnode.attrib['DW_AT_decl_line']), int(dnode.attrib['DW_AT_decl_column']))
		# if DEBUG : print(node_hash)
		dtree_hashmap[node_hash].append(dnode)
	if 'DW_AT_byte_size' in dnode.attrib:
		ddtype[int(dnode.attrib['offset'])] = dnode.attrib['DW_AT_byte_size']
	for child in dnode:
		TraverseDtree(child, filetable)

def try_getting_size_info(dnode) :
	if "DW_AT_byte_size" in dnode.attrib :
		return dnode.attrib["DW_AT_byte_size"]
	if "DW_AT_type" in dnode.attrib :
		ref_offset = int(dnode.attrib["DW_AT_type"])
		ref_dnode = ddref[ ref_offset ] if ref_offset in ddref else None
		if ref_dnode is not None :
			ret = try_getting_size_info(ref_dnode)
			if ret != -1 : return ret
	if "DW_AT_specification" in dnode.attrib :
		ref_offset = int(dnode.attrib["DW_AT_specification"])
		ref_dnode = ddref[ ref_offset ] if ref_offset in ddref else None
		if ref_dnode is not None :
			ret = try_getting_size_info(ref_dnode)
			if ret != -1 : return ret
	return -1

def patch_offset(cnode, dnode):
	if 'DW_AT_location' in dnode.attrib:
		m = dnode.attrib['DW_AT_location'].split()
		if m[-2] == 'DW_OP_addr' and address:
			cnode.set('address', int(m[-1]))
		elif m[-2] == 'DW_OP_fbreg' and offset:
			cnode.set('offset', (abs(int(m[-1]) + 16)))
		return True
	elif 'DW_AT_data_member_location' in dnode.attrib:
		cnode.set('offset', dnode.attrib['DW_AT_data_member_location'])
		return dnode
	elif not ('DW_AT_external' in dnode.attrib and 'yes' in dnode.attrib['DW_AT_external']) and DEBUG:
		print ('OFFSET NOT FOUND: ', cnode, cnode.attrib, dnode.attrib)
	# TODO : see also `grep "DW_AT" pyelftools/elftools/dwarf/enums.py | grep "location"`
	return None

def patch_size(cnode, dnode):
	type_size = try_getting_size_info(dnode)
	if type_size != -1 :
		cnode.set("size", type_size)
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
			print("MULTIPLE MATCHES:", cloc, match)
	return None


def UpdateCtree (cnode, filename=None, lineno = None,colno = None):
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
			elif DEBUG:
				if 'spelling' in cnode.attrib:
					print ('match NOT FOUND ', cloc, cnode.tag, cnode.attrib['spelling'])
	for child in cnode:
		UpdateCtree(child,filename,lineno,colno)

TraverseDtree(droot, [None])

# for k, v in dtree_hashmap.items():
# 	if len(v) > 1:
# 		print ('\n\n', k)
# 		for node in v:
# 			print ('\n', node.tag)
# 			for k, v in node.attrib.items():
# 				print (k, ':', v)


UpdateCtree(croot)

# write out updated xml
xmlstr = minidom.parseString(ET.tostring(croot)).toprettyxml(indent='   ')
with open(combined_filename, 'w') as f:
	f.write(xmlstr)

