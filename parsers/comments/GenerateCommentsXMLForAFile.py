import sys
import re
import glob
import os
import shutil

if __name__ == "__main__":

	DEBUG = False

	if len(sys.argv) != 6:
		print("Give 5 arguments: srcfilename, clangfilename, vocab location, problem domain location, projectName - in this order")
		exit(-1)

	cfilename = sys.argv[1]
	clangfilename = sys.argv[2]
	vocab_loc = sys.argv[3]
	prob_loc = sys.argv[4]
	projectName = sys.argv[5]

	if os.path.isfile(filename) == False:
		print("Error", filename, " is not a valid filename")
		exit(-1)

	try :
		x = os.system("python2 XML_CommentExtractor.py " + cfilename)
		if DEBUG:
			print("CommentExtractor " + str(x))
		if x != 0 :
			exit(-1)

		x = os.system("python2 XML_ScopeModule.py " + cfilename)
		if DEBUG:
			print("XML_ScopeModule " + str(x))
		if x != 0 :
			exit(-1)

		x = os.system("python2 Identifier/xmlparser_with_id.py " + " " + cfilename + " " + clangfilename + " " + vocab + " " + prob_loc)
		if DEBUG:
			print("Identifier " + str(x))
		if x != 0 :
			exit(-1)

		x = os.system("python2 XML_FinalExcelGeneration_with_id.py " + filename + " " + vocab_loc + " " + prob_loc)
		if DEBUG:
			print("Final Knowledge " + str(x))
		if x != 0 :
			exit(-1)

		project_path = cfilename[:cfilename.find(projectName) + len(projectName)]
		knowledgeFile = os.path.splitext(cfilename)[0] + "_knowledgeBase_commentsXML.csv"
		x = os.system("python2 GetFinalXMLForComments.py " + projectName + " " + project_path + " " + cfilename + "  " + knowledgeFile)
		if DEBUG:
			print("XML Generation " + str(x))
		if x != 0 :
			exit(-1)

	except Exception as e :
		print("Error in running the command " + str(e))
		exit(-1)
	exit(0)
