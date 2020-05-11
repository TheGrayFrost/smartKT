#!/usr/bin/env python3

# To use:
# python3 pass2.py <dump file> <output file>

import sys
from xml.etree.ElementTree import Element, SubElement
from xml.etree import ElementTree as ET
from xml.dom import minidom

filename = str(sys.argv[1])		# event trace dump file
outfile = str(sys.argv[2])		# output file

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
		print (' '.join(t))
	i += 1
	while i < len(t):
		if t[i] == 'INP':
			j = i+1
			ipend = t.index('RUNID')
			ipstr = ' '.join(t[i+1:ipend])
			for myloop in range(i+1,ipend):
				t.pop(i+1)
			t.insert (i+1, ipstr)
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
			h = (en.attrib['VARID'], en.attrib['VAROFFSET'])
			if h not in p:
				p[h] = {'WRITE': 0, 'READ': 0, 'FIRSTREAD': 'UND', 'FIRSTWRITE': 'UND'}
				for att in ['VARNAME', 'VAROFFSET']:
					p[h][att] = en.attrib[att]
			p[h][en.tag] += 1
			if p[h]['FIRST'+en.tag] == 'UND':
				p[h]['FIRST'+en.tag] = en.attrib['TS']
		else:
			en.tag = 'NONLOCAL' + en.tag
			entry.append(en)
	
	for var in p.items():
		access = SubElement(entry, 'LOCALACCESS')
		access.attrib['VARID'] = var[0][0]
		access.attrib['WRITECOUNT'] = str(var[1]['WRITE'])
		access.attrib['READCOUNT'] = str(var[1]['READ'])
		for att in ['VARNAME', 'VAROFFSET', 'FIRSTREAD', 'FIRSTWRITE']:
			access.attrib[att] = var[1][att]
	# print entry.tag, entry.attrib
	# for child in entry:
	# 	print child.tag, child.attrib
	return entry

# read the event trace
with open(filename, 'r') as inf, open(outfile, 'w') as opf:
	header = inf.readline()
	hxml = to_xml(header)
	opf.write ('<'+hxml.tag+' '+' '.join([u+'="'+hxml.attrib[u]+'"' for u in hxml.attrib])+'>\n')
	# exit()
	if DEBUG:
		print ('cool')
	ctxt = None
	para = []
	for line in inf:
		entry = to_xml(line)
		if entry is not None:
			u = entry.attrib['TS']
			rl = u.rfind('_')
			rid = int(u[rl+1:])
			if rid % 100 == 0:
				print (u, '\r', end='')
			# print(entry.tag)
			if entry.tag == 'WRITE' or entry.tag == 'READ':
				curctxt = (entry.attrib['THREADID'], entry.attrib['FUNCNAME'], 
					entry.attrib['INVNO'], entry.attrib['SYNCS'])
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
				try:
					xmlstr = minidom.parseString(ET.tostring(entry)).toprettyxml(indent='   ')
				except Exception as e:
					print (ET.tostring(entry))
					exit()
					# pass
				xmlstr = '\n'.join(['   '+l for l in xmlstr.split('\n')[1:-1]])
				opf.write(xmlstr+'\n')
	if ctxt is not None:
		para_entry = process_para(para, ctxt)
		if DEBUG:
			print(ET.tostring(para_entry))
		xmlstr = minidom.parseString(ET.tostring(para_entry)).toprettyxml(indent='   ')
		xmlstr = '\n'.join(['   '+l for l in xmlstr.split('\n')[1:-1]])
		opf.write(xmlstr+'\n')
	opf.write('</'+hxml.tag+'>\n')
	print ()