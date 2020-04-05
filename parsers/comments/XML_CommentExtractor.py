import pickle
import sys, os
import re

def getComments(filename):

	file = open(filename , "r")
	text = file.read()
	file.close()
	file = open(filename , "r")
	lines = file.readlines()
	file.close()

	all_comments = re.compile( r'//.*?$|/\*.*?\*/', re.DOTALL | re.MULTILINE).findall(text)
	comment_iterator = re.compile( r'//.*?$|/\*.*?\*/', re.DOTALL | re.MULTILINE)
	l = [(m.start(0), m.end(0)) for m in re.finditer(comment_iterator, text)]	

	start_line = []
	end_line = []
	for pos in range(0, len(all_comments)):
		location = l[pos][0]
		s = text[:location + 1]
		lineNo1 = s.count('\n') + 1
		location1 = l[pos][1]
		s = text[:location1 + 1]
		lineNo2 = s.count('\n')
		start_line.append(lineNo1)
		end_line.append(lineNo2)

		if all_comments[pos].startswith("//"):
			all_comments[pos] = all_comments[pos][2:]
		else:
			all_comments[pos] = all_comments[pos][2:-2]

		all_comments[pos] = all_comments[pos].strip()


	result = []

	for pos in range(0, len(all_comments)):

		text = all_comments[pos]
		start = start_line[pos]
		end = end_line[pos]

		if end < start:
			end = start
			
		#bundling consecutive single line comments
		if len(result) > 0 and lines[start - 1].strip().startswith("//") and result[-1][2] == start - 1:
			result[-1][0] = result[-1][0] + "\n" + text
			result[-1][2] = start

		else:
			result.append([text, start, end])

	return result

def main():
	if len(sys.argv) != 3:
		print("Give 2 inputs: src_file_name outputprefix - in this order")
		exit(-1)
	srcfilename = sys.argv[1]
	outputprefix = sys.argv[2]
	comments = getComments(srcfilename)
	pickle.dump(comments, open( outputprefix+"_comments.p", "wb" ))

main()
