#!/usr/bin/env python
# To use:
# python clang_parser.py <filename> -I/a/a/ -I<more dependency>

import sys

import clang.cindex as cl
from clang.cindex import Index
from pprint import pprint
from optparse import OptionParser, OptionGroup
from xml.etree.ElementTree import Element, SubElement
from xml.etree import ElementTree as ET
from xml.dom import minidom
from collections import defaultdict
import re

# Set the clang shared object. The python interface is just a proxy for the actual clang
cl.Config.set_library_file('/usr/local/lib/libclang.so')

# collector for all calls on a line
calls = defaultdict(set)

# collector for all function signatures
signs = []

def getsign(func):
  # FILENAME FUNCNODEID FUNCNAME NARGS ARGTYPE* RETTYPE 
  if 'mangled_name' in func.attrib:
      func_name = func.attrib['mangled_name']
  else:
      func_name = func.attrib['spelling']
  row = func.attrib['location'].split('[')[0] + '\t'
  row += func.attrib['id'] + '\t'
  row += func_name + '\t'
  ret = (func.attrib['type'].split('('))[0]
  argc = 0
  args = ''
  for parm in func:
      if parm.tag == 'PARM_DECL':
          argc += 1
          args += ('\t' + parm.attrib['type'])
  row += str(argc) + args + '\t' + ret.strip()
  return row


# Recursively visit each node and its children and store its information in a XML tree
def get_info(node, parent):
  global func_node, s
  try:
    sub = SubElement(parent, str(node.kind.name))
  except:
    sub = SubElement(parent, 'Unknown')
# These are the list of attributes we are keeping track of. This becomes better
# with the intuitive parser  
  nodeid = node.hash
  if node.referenced is not None:
    if nodeid != node.referenced.hash:
      nodeid = node.referenced.hash
  sub.set('id', str(nodeid))

  if node.semantic_parent is not None:
    sub.set('parent_id', str(node.semantic_parent.hash))
  if node.lexical_parent is not None:
    sub.set('lex_parent_id', str(node.lexical_parent.hash))
  sub.set('usr', 'None' if node.get_usr() is None else str(node.get_usr()))
  sub.set('spelling', 'None' if node.spelling is None else str(node.spelling))
  sub.set('location', 'None' if (node.location is None or node.location.file is None) else str(node.location.file)+'['+str(node.location.line)+']')
  sub.set('linenum', 'None' if (node.location.line is None) else str(node.location.line))
  sub.set('extent.start', 'None' if (node.extent.start is None or node.extent.start.file is None) else str(node.extent.start.file)+'['+ str(node.extent.start.line) + ']')
  sub.set('extent.end', 'None' if (node.extent.end is None or node.extent.end.file is None) else str(node.extent.end.file)+'['+ str(node.extent.end.line) + ']')
  sub.set('is_definition', str(node.is_definition()))
  # print ('this worked', parent.tag, node.kind.name, node.spelling, node.location.file, node.location.line)
  if node.access_specifier.name not in ['NONE', 'INVALID']:
    sub.set('access_specifier', node.access_specifier.name)  
  if node.storage_class.name not in ['NONE', 'INVALID']:
    sub.set('storage_class', str(node.storage_class.name))
  # if node.linkage.name not in ['NO_LINKAGE', 'INVALID']:
  #   sub.set('linkage', str(node.linkage.name))
  # if node.mangled_name is not None and len(node.mangled_name) > 0:
  #   sub.set('mangled_name', str(node.mangled_name))
  # try:
  if node.type.spelling is not None:
    sub.set('type', str(node.type.spelling))
    # sub.set('size', str(node.type.get_size()))
  children = [get_info(c, sub) for c in node.get_children()]

#   # save all calls
#   try:
#     if node.kind.name == 'CALL_EXPR':
#       callexp = ''.join(re.sub('\t', ' ', tok.spelling) for tok in node.get_tokens())
#       if callexp != '':
#         calls[(node.location.file, node.location.line, node.spelling)].add((str(nodeid), callexp))
#   except ValueError as e: # in case node.kind does not have a name
#     pass
# 
#   except Exception as e:
#     print('\n\nException occured', e)
#     print ('\n\nhere: ', parent.tag, node.kind.name, node.spelling, node.location.file, node.location.line)
#     print ('\n\n')

# 
#   # collect all function signatures, after you have parsed the child params also
#   try:
#     if node.kind.name == 'FUNCTION_DECL' or node.kind.name == 'CXX_METHOD':
#       s = getsign(sub)
#       signs.append(s)
#       # if(len(s) == 0):
#       #   print ('dafuq')
#       #   print (sub.attrib)
#   except ValueError as e: # in case node.kind does not have a name
#     pass

  return parent

# Helps parse the dependency in here
# parser = OptionParser('usage: %prog [options] {filename} [clang-args*]')
# parser.disable_interspersed_args()
# (opts, args) = parser.parse_args()


# input options in form: <file to parse> <dependency list> <xml_extension> <calls_ext> <finfo_ext>
# python sys.argv[0] source.ast
f = sys.argv[0]
astfile = sys.argv[-1]
# print (infile)
# infilestrip = f[:f.rfind('.')]
# xmlext = args[-3]
# callext = args[-2]
# finfoext = args[-1]

# Get the translation unit
index = Index.create()
# tu = index.read(astfile)
tu = index.parse(None, astfile)

if not tu:
  parser.error('unable to load input')

root = Element('STATICROOT')
root = get_info(tu.cursor, root)
root.set('id', str(0))
# print(ET.tostring(root, encoding='utf8').decode('utf8'))

# Emit all the calls
# outcallname = infilestrip + callext
# with open(outcallname, 'w') as f:
#   f.write('# FILENAME\tLINENUM\tFUNCNAME\tCALLNODEID\tCALLEXPR\n')
#   for k, v in calls.iteritems():
#     for u in v:
#       f.write('%s\t%s\t%s\t%s\t%s\n' % (k[0], k[1], k[2], u[0], u[1]))
# 
# # Emit all the signatures
# outfinfoname = infilestrip + finfoext
# with open(outfinfoname, 'w') as f:
#   f.write('# FILENAME\tFUNCNODEID\tFUNCNAME\tNARGS\tARGTYPE*\tRETTYPE\n')
#   for row in signs:
#     f.write(row + '\n')
# 
# 
# For pretty representation and writing to output
xmlstr = minidom.parseString(ET.tostring(root)).toprettyxml(indent='   ')
print(xmlstr)
# with open(outxmlname, 'w') as f:
#     f.write(xmlstr)
# print('The entire XML parse has been written at ', outfilename)

