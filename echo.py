#!/usr/bin/env python3

import pickle as pckl
import re
import os, sys

dep = pckl.load(open(sys.argv[1], 'rb'))
# , src, obj)

for k, v in dep.items():
	print (k)
	if isinstance(v, set):
		for u in v:
			print ('\t', u)
	elif isinstance(v, dict):
		for u in v.items():
			print ('\t', u)
	else:
		print ('\t', v)

exit()

cins = dep


for i, ins in enumerate(cins):
	# print(ins)
	if 'lib1503' in ins:
		print(ins)
		print('\t', cins[ins])
exit()

ins = cins['/data/user-home/srijoni/PIN_Tests/smartKT/projects/curl/build/tests/libtest/lib1521.c']
# print(ins)

cmd = ins['command'].split(' ')
clangv = 'clang'

# Get the objectfile
f = ins['file']
objectfile = ins.get('object', None)
if objectfile is None:
    objectfile = cmd[cmd.index('-o')+1]
if not os.path.isabs(objectfile):
    objectfile = os.path.abspath(os.path.join(ins['directory'], objectfile))

# Update the command to emit ast
mainfname = f[f.rfind('/')+1:f.rfind('.')]
cmd[0] = clangv + ' -emit-ast'
cmd[cmd.index('-o')+1] = mainfname + '.ast'

# Remove flags that cause errors
cmd = ' '.join([x for x in cmd if x not in ['-flifetime-dse=1']])
print(mainfname)
os.system(cmd)
path = '/data/user-home/srijoni/PIN_Tests/smartKT/projects/curl'
outfolder = '/data/user-home/srijoni/PIN_Tests/smartKT/outputs/curl'

relpath = f[len(path)+1:]
outpath = os.path.join(outfolder, relpath)
print (outpath)

stripop = os.path.join(outpath, mainfname)

DWARFTOOL = 'dwxml.py'
COMBINER = 'saved_ddx.py'
PROJPARSER = 'project_parser.py'

# output extensions
CLANG_EXTENSION = '_clang.xml'
DWARF_EXTENSION = '_dd.xml'
COMB_EXTENSION = '_comb.xml'
CALL_TEMP_EXTENSION = '.calls.temp'
CALL_FINAL_EXTENSION = '.calls.tokens'
SIGN_EXTENSION = '.funcargs'
OFFSET_EXTENSION = '.offset'

os.system(' '.join(['parsers/ast2xml', str(241), f, mainfname+'.ast',
                            stripop+CALL_TEMP_EXTENSION, stripop+CLANG_EXTENSION ]))

print('output :' + stripop + CLANG_EXTENSION + '\n')
print('output :' + stripop + CALL_TEMP_EXTENSION + '\n')


# print (src)
# print ('\n\n\n')
# print (obj)
# print ('\n\n\n')

# mydep = dict()
# for k, v in dep.items():
# 	k = re.sub('workspace', 'data/user-home/srijoni/PIN_Tests/smartKT', k)
# 	v = [re.sub('workspace', 'data/user-home/srijoni/PIN_Tests/smartKT', el) for el in v]
# 	mydep[k] = v

# mysrc = dict()
# for k, v in src.items():
# 	k = re.sub('workspace', 'data/user-home/srijoni/PIN_Tests/smartKT', k)
# 	v = re.sub('workspace', 'data/user-home/srijoni/PIN_Tests/smartKT', v)
# 	mysrc[k] = v

# myobj = dict()
# for k, v in obj.items():
# 	k = re.sub('workspace', 'data/user-home/srijoni/PIN_Tests/smartKT', k)
# 	v = re.sub('workspace', 'data/user-home/srijoni/PIN_Tests/smartKT', v)
# 	myobj[k] = v

# pckl.dump((mydep, mysrc, myobj), open('dependencies.p', 'wb'))
# print ('Rewrote dep.p')