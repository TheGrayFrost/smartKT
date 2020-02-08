#!/usr/bin/env python

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

ddtype = dict()
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

#variable comparison basis
def dnode_hash(v):
	# if DEBUG:
	# 	print (v.tag, v.attrib['name'], v.attrib['decl_file'].split()[1], 
	# 		int(v.attrib['decl_line'], 16), int(v.attrib['decl_column'], 16), v.attrib['id'])
	return (' '.join(v.attrib['decl_file'].split()[1:]), #if filename contains spaces 
		int(v.attrib['decl_line'], 16), int(v.attrib['decl_column'], 16))

def TraverseDtree(dnode, level=0): # collect all pokemon in dtree
	if 'decl_file' in dnode.attrib: # covers everything except enum const, which are not needed anyway
		dtree_hashmap[dnode_hash(dnode)].append(dnode)
	if 'byte_size' in dnode.attrib:
		ddtype[dnode.attrib['id']] = dnode.attrib['byte_size']
	# if dnode.tag == 'typedef':
	# 	ddtype[dnode.attrib['id']] = ('typedef', dnode.attrib['type'])
	for child in dnode:
		TraverseDtree(child,level+1)

def patchTypedefSize(v):
	if isinstance(v, tuple):
		ddtype[v[0]] = patchTypedefSize(ddtype[v[1]])
	return ddtype[v[0]]

def cnode_hash (cnode, ctxt):
	if 'line' in cnode.attrib and 'col' in cnode.attrib:
		return (ctxt, int(cnode.attrib['line']), int(cnode.attrib['col']))
	return ''

def patch_offset(cnode, dnode):
	if 'location' in dnode.attrib:
		m = dnode.attrib['location'].split()
		if m[-2] == 'DW_OP_addr' and address:
			cnode.set('address', hex(int(m[-1], 16)))
		elif m[-2] == 'DW_OP_fbreg' and offset:
			cnode.set('offset', hex(abs(int(m[-1], 10) + 16)))
		return True
	else:
		return False

def patch_size(cnode, dnode):
	if dnode.attrib['type'] in ddtype:
		cnode.set('size', ddtype[dnode.attrib['type']])
		return True
	else:
		return False

def get_match(cloc):
	if cloc in dtree_hashmap:
		match = dtree_hashmap[cloc]
		if len(match) == 1:
			return match[0]
	return None

def UpdateCtree (cnode, level=0, ctxt=''):
	if 'file' in cnode.attrib:
		ctxt = cnode.attrib['file']
	if cnode.tag in All:
		cloc = cnode_hash(cnode, ctxt)
		if cloc != '':
			match = get_match(cloc)
			if match is not None:
				print ('FOUND ', cloc, cnode.attrib['spelling'], match.attrib['id'])
				if cnode.tag in Variables:
					patch_offset(cnode, match)
					patch_size(cnode, match)
			elif DEBUG:
				if 'spelling' in cnode.attrib:
					print ('NOT FOUND ', cloc, cnode.tag, cnode.attrib['spelling'])
	for child in cnode:
		UpdateCtree(child,level+1,ctxt)

TraverseDtree(droot)
# for k, v in ddtype.items():

UpdateCtree(croot)

# write out updated xml
xmlstr = minidom.parseString(ET.tostring(croot)).toprettyxml(indent='   ')
with open(combined_filename, 'w') as f:
	f.write(xmlstr)

