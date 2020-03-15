import sys
import re
import glob
import os
import shutil

if __name__ == "__main__":

	DEBUG = False

	if len(sys.argv) != 5:
		print("Give 4 arguments: srcfilename, vocab location, problem domain location, projectName - in this order")
		exit(-1)

	cfilename = sys.argv[1]
	clangfilename = os.path.splitext(sys.argv[1])[0] + "_comb.xml"
	vocab_loc = sys.argv[2]
	prob_loc = sys.argv[3]
	projectName = sys.argv[4]

	if os.path.isfile(cfilename) == False:
		print("Error", cfilename, " is not a valid filename")
		exit(-1)

	try :
		x = os.system("python3 XML_CommentExtractor.py " + cfilename)
		if DEBUG:
			print("CommentExtractor " + str(x))
		if x != 0 :
			exit(-1)

		x = os.system("python3 XML_ScopeModule.py " + cfilename)
		if DEBUG:
			print("XML_ScopeModule " + str(x))
		if x != 0 :
			exit(-1)

		x = os.system("python3 xmlparser_with_id.py " + " " + cfilename + " " + clangfilename + " " + vocab_loc + " " + prob_loc)
		if DEBUG:
			print("Identifier " + str(x))
		if x != 0 :
			exit(-1)

		x = os.system("python3 XML_FinalExcelGeneration_with_id.py " + cfilename + " " + vocab_loc + " " + prob_loc)
		if DEBUG:
			print("Final Knowledge " + str(x))
		if x != 0 :
			exit(-1)

		project_path = cfilename[:cfilename.find(projectName) + len(projectName)]
		knowledgeFile = os.path.splitext(cfilename)[0] + "_knowledgeBase_commentsXML.csv"
		x = os.system("python3 GetFinalXMLForComments.py " + projectName + " " + project_path + " " + cfilename + "  " + knowledgeFile)
		if DEBUG:
			print("XML Generation " + str(x))
		if x != 0 :
			exit(-1)

		print("Comments Analyzed: "+cfilename)
	except Exception as e :
		print("Error in running the command " + str(e))
		exit(-1)
	exit(0)
