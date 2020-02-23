#!/usr/bin/env python3

import pickle as pckl
import re
import sys

dep = pckl.load(open(sys.argv[1], 'rb'))
# , src, obj)

for k, v in dep.items():
	print (k)
	if (isinstance(v, set)):
		for u in v:
			print ('\t'+u)
	else:
		print ('\t'+v)

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