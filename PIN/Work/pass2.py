#!/usr/bin/env python3

import sys
from xml.etree.ElementTree import Element, SubElement
from xml.etree import ElementTree as ET
from xml.dom import minidom

filename = str(sys.argv[1])		# event trace dump file

DEBUG = False

def to_xml(line):
	t = line.split()
	i = 0
	entry = Element(t[i])	# first word is event type
	if t[0] == 'CALL':
		# collect static calls
		statbeg = t.index('[')
		statend = len(t) - 1 - t[::-1].index(']') 
		if statbeg != -1:
			stat = ' '.join(t[statbeg:statend+1])
		for inloop in range(statbeg,statend+1):
			t.pop(statbeg)
		t.insert(statbeg, stat)
		if DEBUG:
			print ('\n'.join(t))
	i += 1
	while i < len(t):
		entry.attrib[t[i]] = t[i+1]	 # all other events come in key:value pairs
		if t[i] == 'SYNCS' and t[i+1] != 'ASYNC':	# synchronization locks are kept as children of events
			k = int(t[i+1])							# get number of locks
			i += 2
			for j in range(k):						# add a child for each lock held
				lock = SubElement(entry, 'POSIXLOCK')
				lock.attrib[t[i]] = t[i+1]			# lock type
				i += 2
				lock.attrib[t[i]] = t[i+1]			# lock address
				i += 2
		else:
			i += 2
	# if 'OFFSET' in entry.attrib:					# get variable id info from the offset
	# 	t = (entry.attrib['FUNCNAME'], entry.attrib['OFFSET'])
	# 	if t in varmap:
	# 		entry.attrib['VARID'] = varmap[t]
	# 	else:										# if not found in the map
	# 		entry = None							# don't write
	return entry

def process_para(para, ctxt):
	
	entry = Element('IO')
	entry.attrib['THREADID'] = ctxt[0]
	entry.attrib['FUNCNAME'] = ctxt[1]
	entry.attrib['INVNO'] = ctxt[2]
	entry.attrib['SYNCS'] = ctxt[3]
	p = dict()
	for en in para:
		if en.attrib['VARCLASS'] == 'LOCAL': # collect all local accesses
			h = en.attrib['VARID'] 
			if h not in p:
				p[h] = {'WRITE': 0, 'READ': 0}
				for att in ['VARNAME', 'OFFSET']:
					p[h][att] = en.attrib[att]
			p[h][en.tag] += 1
		else:
			en.tag = "NONLOCAL" + en.tag
			entry.append(en)
	
	for var in p.items():
		access = SubElement(entry, 'LOCALACCESS')
		access.attrib['VARID'] = var[0]
		access.attrib['WRITECOUNT'] = str(var[1]['WRITE'])
		access.attrib['READCOUNT'] = str(var[1]['READ'])
		for att in ['VARNAME', 'OFFSET']:
			access.attrib[att] = var[1][att]
	# print entry.tag, entry.attrib
	# for child in entry:
	# 	print child.tag, child.attrib
	return entry

# read the event trace
with open(filename, 'r') as inf, open('dynamic.xml', 'w') as opf:
	# add run info
	head = to_xml(inf.readline())
	opf.write('<' + head.tag + ' ' + ' '.join([f'{u}="{v}"' for (u,v) in head.attrib.items()]) + '>\n')
	# now start life
	if DEBUG:
		print ('cool')
	ctxt = None
	para = []
	for line in inf:
		entry = to_xml(line)
		if entry is not None:
			print (entry.attrib['id'], '\r', end='')
			if entry.tag == 'WRITE' or entry.tag == 'READ':
				curctxt = (entry.attrib['THREADID'], entry.attrib['FUNCNAME'], entry.attrib['INVNO'], entry.attrib['SYNCS'])
				if ctxt is None:
					ctxt = curctxt
				if ctxt == curctxt:
					para.append(entry)
			else:
				if ctxt is not None:
					para_entry = process_para(para, ctxt)
					xmlstr = minidom.parseString(ET.tostring(para_entry)).toprettyxml(indent='   ')
					xmlstr = '\n'.join(['   '+l for l in xmlstr.split('\n')[1:-1]])
					opf.write(xmlstr+'\n')
					para = []
					ctxt = None
				if DEBUG:
					print ('wow')
					print (ET.tostring(entry))
				xmlstr = minidom.parseString(ET.tostring(entry)).toprettyxml(indent='   ')
				# except Exception as e:
				# 	print (ET.tostring(entry))
				# 	exit()
				xmlstr = '\n'.join(['   '+l for l in xmlstr.split('\n')[1:-1]])
				opf.write(xmlstr+'\n')
	if ctxt is not None:
		para_entry = process_para(para, ctxt)
		if DEBUG:
			print(ET.tostring(para_entry))
		xmlstr = minidom.parseString(ET.tostring(para_entry)).toprettyxml(indent='   ')
		xmlstr = '\n'.join(['   '+l for l in xmlstr.split('\n')[1:-1]])
		opf.write(xmlstr+'\n')
	opf.write('</DYNAMICROOT>\n')
	print ()