#!/usr/bin/env python3

# To use:
# python3 GenerateCommentsXMLForAFile.py <source_file> <output_file> <vocab_file> 
# <problem_domain_file> <project_name>

import sys
import re
import glob
import os
import shutil

if __name__ == "__main__":

	DEBUG = False

	if len(sys.argv) != 6:
		print("Give 5 arguments: srsrcfilename, outputprefix, vocab location, problem domain location, projectName - in this order")
		exit(-1)

	srcfilename = sys.argv[1]
	outputprefix = sys.argv[2]
	vocab_loc = sys.argv[3]
	prob_loc = sys.argv[4]
	projectName = sys.argv[5]

	if os.path.isfile(srcfilename) == False:
		print("Error", srcfilename, " is not a valid filename")
		exit(-1)

	try :
		x = os.system("python3 XML_CommentExtractor.py " + srcfilename + " " + outputprefix)
		if DEBUG:
			print("CommentExtractor " + str(x))
		if x != 0 :
			exit(-1)

		x = os.system("python3 XML_ScopeModule.py " + srcfilename + " " + outputprefix)
		if DEBUG:
			print("XML_ScopeModule " + str(x))
		if x != 0 :
			exit(-1)

		x = os.system("python3 xmlparser_with_id.py " + " " + srcfilename + " " +  \
			outputprefix+"_comb.xml" + " " + outputprefix + " " + vocab_loc + " " + prob_loc)
		if DEBUG:
			print("Identifier " + str(x))
		if x != 0 :
			exit(-1)

		x = os.system("python3 XML_FinalExcelGeneration_with_id.py " + srcfilename + " "+ outputprefix +" " + vocab_loc + " " + prob_loc)
		if DEBUG:
			print("Final Knowledge " + str(x))
		if x != 0 :
			exit(-1)

		project_path = srcfilename[:srcfilename.find(projectName) + len(projectName)]
		x = os.system("python3 GetFinalXMLForComments.py " + projectName + " " + project_path + " " + srcfilename + "  " + outputprefix)
		if DEBUG:
			print("XML Generation " + str(x))
		if x != 0 :
			exit(-1)

		print("Comments Analyzed: "+srcfilename)
	except Exception as e :
		print("Error in running the command " + str(e))
		exit(-1)
	exit(0)
