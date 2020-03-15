import sys, os
from os.path import join as PJOIN
import pickle



def runForFolder(folder_name):
    for file in os.listdir(folder_name):
        if os.path.isdir(folder_name):
            runForFolder(PJOIN(folder_name, file))
            continue
        (filename, ext) = os.path.splitext(file)
        if ext not in ['c', 'C', 'cc', 'cpp', 'cxx', 'c++']:
            continue
        if not IS_FRESH and os.path.exists(filename+"_comments.xml"):
            print("Skipping: Already Exists: ", filename+"_comments.xml")
            continue
        os.system("python2 GenerateCommentsXMLForAFile.py " + file + " " + VOCAB_FILE + " " + PROBLEM_DOMAIN_FILE + " " + PROJECT_NAME)

if len(sys.argv) != 4:
    print("Give 3 arguments: PROJECT_SOURCE(containing the Clang), VOCAB_FILE, PROBLEM_DOMAIN_FILE - in this order")
    exit(-1)


# Fresh Run
IS_FRESH = True

# Input arguments
PROJECT_SOURCE = os.path.abspath(sys.argv[1])
VOCAB_FILE = os.path.abspath(sys.argv[2])
PROBLEM_DOMAIN_FILE = os.path.abspath(sys.argv[3])
PROJECT_NAME = os.path.abspath(sys.argv[4])

runForFolder(PROJECT_SOURCE)
