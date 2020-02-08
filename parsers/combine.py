from xml.etree.ElementTree import Element, SubElement
from xml.etree import ElementTree as ET
from xml.dom import minidom
from collections import defaultdict
import sys

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

dtree = ET.parse(dwarfxml_filename)
droot = dtree.getroot()

ctree = ET.parse(clangxml_filename)
croot = ctree.getroot()

dtree_hashmap = defaultdict(list) # contains global constructs hash
dtree_subtree_hash = defaultdict(list) # contains local variables and formal parameter hash

# cnodeUpdateTag = ['FUNCTION_DECL','CXX_METHOD','CONSTRUCTOR','DESTRUCTOR']
cnodeUpdateTag = ['FunctionDecl','CXXMethod','CXXConstructor','CXXDestructor']

#variable comparison basis
def variable_hash(dnode):
	return ('variable', dnode.attrib['decl_file'].split()[1], 
		str(int(dnode.attrib['decl_line'], 16)), dnode.attrib['name'])

#variable comparison basis
def variable_hash_cnode(v):
	return ('variable', v.attrib['location'].split('[')[0], v.attrib['linenum'],v.attrib['spelling'])

# Parameter comparison basis
def parameter_hash(dnode):
	return ('parameter', dnode.attrib['name'])

# Build Hash of all variables and formal parameters of a Scope
def subtree_hash_builder(dnode,cnode):
	if(DEBUG):
		print(dnode,cnode)
	# add variables into hash
	if dnode.tag=='variable' and 'decl_file' in dnode.attrib and 'decl_line' in dnode.attrib:
		dtree_subtree_hash[variable_hash(dnode)].append(dnode)

	# add formal parameters
	if dnode.tag=='formal_parameter':
		if 'name' in dnode.attrib:
			if dnode.attrib['name'] == 'this':
				sub = SubElement(cnode, 'THIS_PARM_ARTIFICIAL')
				sub.set('id', dnode.attrib['id'])
				sub.set('spelling', dnode.attrib['name'])
				try:
					sub.set('offset', str(int(dnode.attrib['location'].split()[-1]) + 16))
					sub.set('linenum', cnode.attrib['linenum'])
					for this_decl in cnode.findall(".//*[@spelling='this']"):
						if(DEBUG):
							print(dnode,this_decl)
						this_decl.set('offset', str(int(dnode.attrib['location'].split()[-1]) + 16))
					
				except Exception as e:
					print(e)
			else:
				dtree_subtree_hash[parameter_hash(dnode)].append(dnode)
	
	for child in dnode:
		subtree_hash_builder(child,cnode)

def patch_offset(cnode, dnode):
	m = dnode.attrib['location'].split()
	if m[-2] == 'DW_OP_addr' and address:
		cnode.set('address', hex(int(m[-1], 16)))
	elif m[-2] == 'DW_OP_fbreg' and offset:
		cnode.set('offset', hex(abs(int(m[-1], 10) + 16)))
	return cnode

def set_offsets_by_hash(cnode, dnode):
	if(DEBUG):
		print(cnode.tag,'   ',dnode.tag)

	if cnode.tag == 'VAR_DECL':
		if 'location' in dnode.attrib:
			cnode = patch_offset(cnode, dnode)
		return cnode

	# Add linkage_name(mangle name) if there:
	if 'linkage_name' in dnode.attrib:
		cnode.set('linkage_name', dnode.attrib['linkage_name'])

	dtree_subtree_hash.clear()
	subtree_hash_builder(dnode,cnode)

	#print(dtree_subtree_hash)
	# Variable declarations
	for v in cnode.findall('.//VAR_DECL'):
		if(DEBUG):
			print(('variable',v.attrib['linenum'],v.attrib['spelling']))
		for var in dtree_subtree_hash[variable_hash_cnode(v)]:
			if(DEBUG):
				print(var,v)
			try:
				v = patch_offset(v, var)
			except Exception as e:
				print ('An Exception occured: ', e)
				print(('variable',v.attrib['linenum'],v.attrib['spelling']))
				print(var)

	for p in cnode.findall('.//PARM_DECL'):
		for parm in dtree_subtree_hash[('parameter',p.attrib['spelling'])]:
			if(DEBUG):
				print(parm,p)
			patch_offset(p, parm)
			# p.set('offset', str(int(parm.attrib['location'].split()[-1]) + 16))
			
	return cnode


def matchNeeded(cnode, level):
	# try:
	#	 if cnode.attrib['spelling'] == 'valid_parameters':
	#		 print (cnode.tag, cnode.attrib)
	#		 print (level)
	#		 print ([u.tag, u.attrib] for u in potential_match)
	# except:
	#	 pass
	if cnode.tag == 'VAR_DECL' and level == 3:
		return True
	return cnode.tag in cnodeUpdateTag

def ExactMatch(cnode,dnode):
	if(DEBUG):
		print('CNODE')
		print(cnode.tag, variable_hash_cnode(cnode))
		print('\nDNODE')
		print(dnode.tag, variable_hash(dnode))
		print '\n\n'
	return True

def GetDNodeHash(dnode):
	return (dnode.attrib['decl_file'].split()[1], str(int(dnode.attrib['decl_line'], 16)), dnode.attrib['name'])

def GetCNodeHash(cnode):
	return (cnode.attrib['location'].split('[')[0], cnode.attrib['linenum'], cnode.attrib['spelling'])

# DFS on the dwarfdump tree to create hashmap

def CreateHashMapDtree(dnode, level):
	if dnode.tag == 'variable' and level == 2 and 'decl_file' in dnode.attrib and 'decl_line' in dnode.attrib and 'name' in dnode.attrib:
		dtree_hashmap[GetDNodeHash(dnode)].append(dnode)
	elif dnode.tag=='subprogram' and 'decl_file' in dnode.attrib and 'decl_line' in dnode.attrib:
		dtree_hashmap[GetDNodeHash(dnode)].append(dnode)
	for child in dnode:
		CreateHashMapDtree(child,level+1)

# DFS on the Clang_tree to update
def UpdateCtree(cnode,level):
	if matchNeeded(cnode, level):
		potential_match = dtree_hashmap[GetCNodeHash(cnode)]
		# if cnode.attrib['spelling'] == 'valid_parameters':
		#	 print (cnode.tag, cnode.attrib)
		#	 print (level)
		#	 print ([u.tag, u.attrib] for u in potential_match)

		if DEBUG:
			# if cnode.tag == 'VAR_DECL':
				# print (variable_hash_cnode(cnode))
				# print (len(potential_match))
			if (len(potential_match) > 0):
				print (variable_hash_cnode(cnode))
				print([(u.tag, u.attrib['name']) for u in potential_match])
			#check in line number hashmap if any potentials
		#can be improved to incorporate tuples as needed
		for dnode in potential_match:
			if ExactMatch(cnode,dnode):
				# match with the first exact match
				set_offsets_by_hash(cnode,dnode)
				break

	for child in cnode:
		UpdateCtree(child,level+1)

# generates string representation of given variable node for linkage with PIN later
def helper(var, var_class, var_container = None):
	# STATIC STORAGE VARIABLE:
	# ADDRESS VARNAME ID TYPE SIZE PARENT_ID CLASS CONTAINER

	# AUTO STORAGE VARIABLE:
	# FILENAME FUNCTION OFFSET VARNAME ID TYPE SIZE PARENT_ID   
	s = ''
	if var_class == 'LOCAL':
		s += var.attrib['location'].split('[')[0] + '\t'
		s += var_container + '\t'
		s += var.attrib['offset'] + '\t'
	else:
		s = var.attrib['address'] + '\t'

	var_name = (var.attrib['mangled_name'] if ('mangled_name' in var.attrib) else var.attrib['spelling'])
	s += var_name + '\t'
	s += var.attrib['id'] + '\t'
	s += var.attrib['type'] + '\t'
	var_size = '0'
	if 'size' in var.attrib :
	var_size = var.attrib['size']
	s += var_size + '\t'
	s += var.attrib['parent_id'] + '\t'

	if var_class != 'LOCAL':
		s += var_class
		if var_container is not None:
			s += '\t' + var_container
	
	s += '\n'
	return s

def generate_var(croot):
	with open(outemits_filename, 'w') as f:
		if address:
			# writing globals
			# ADDRESS VARNAME ID TYPE SIZE PARENT_ID CLASS CONTAINER
			f.write('# ADDRESS\tVARNAME\tVARID\tVARTYPE\tVARSIZE\tPARENTID\tVARCLASS\t[VARCONTAINER]\n')

			printed = set()	
			# First out all global variables
			# Mention any address only once
			s = ''
			for var in croot.findall('.//TRANSLATION_UNIT/VAR_DECL[@address]'):
				if var.attrib['address'] not in printed:
					printed.add(var.attrib['address'])
					if DEBUG:
						print (var.attrib['address'])
					if 'storage_class' in var.attrib and var.attrib['storage_class'] == 'STATIC':
						s += helper(var, 'STATIC')
					# mention globals only once
					else:
						if 'mangled_name' in var.attrib:
							var_name = var.attrib['mangled_name']
						else:
							var_name = var.attrib['spelling']
						s += helper(var, 'GLOBAL')
			f.write(s)

			# Static storage variables inside containers
			VARCONTAINERS = {'FUNCTION_DECL':'FUNCSTATIC', 'CXX_METHOD':'FUNCSTATIC',
								'CONSTRUCTOR':'FUNCSTATIC', 'DESTRUCTOR':'FUNCSTATIC',
								'CLASS_DECL':'CLASSSTATIC', 'STRUCT_DECL':'STRUCTSTATIC'}

			for nodetype, store in VARCONTAINERS.iteritems():
				# Get all static variables inside
				s = ''
				for obj in croot.findall('.//'+nodetype):
					obj_name = (obj.attrib['mangled_name'] if ('mangled_name' \
										in obj.attrib) else obj.attrib['spelling'])
					for var in obj.findall('.//VAR_DECL[@address]'):
						if var.attrib['address'] not in printed:
							printed.add(var.attrib['address'])
							if DEBUG:
								print (var.attrib['address'])
							s += helper(var, store, obj_name)
				f.write(s)
	# Address

		if offset:
			# For all local variable declarations
			# FUNCTION OFFSET VARNAME ID TYPE SIZE PARENT_ID
			f.write('# FILENAME\tFUNCTION\tOFFSET\tVARNAME\tVARID\tVARTYPE\tVARSIZE\tPARENTID\n')

		LOCALVARCONTAINERS = cnodeUpdateTag
			VARNODETYPE = ['VAR_DECL', 'PARM_DECL']

			for nodetype in LOCALVARCONTAINERS:
				s = ''
				for func in croot.findall('.//'+nodetype):
					func_name = func.attrib['spelling']
					if 'mangled_name' in func.attrib:
						func_name = func.attrib['mangled_name']
					elif 'linkage_name' in func.attrib:
						func_name = func.attrib['linkage_name'] 
					for varnt in VARNODETYPE:
						for var in func.findall('.//' + varnt + '[@offset]'):
							s += helper(var, 'LOCAL', func_name)
				if(len(s) > 0):
					f.write(s)
	# Offset

CreateHashMapDtree(droot,0)
# if(DEBUG):
#	 for k, v in dtree_hashmap.iteritems():
#		 print(k, [(u.tag, u.attrib['name']) for u in v])
UpdateCtree(croot,0)

# write out updated xml
xmlstr = minidom.parseString(ET.tostring(croot)).toprettyxml(indent='   ')
with open(combined_filename, 'w') as f:
	f.write(xmlstr)

# write out updated address/offset file
generate_var(croot)

