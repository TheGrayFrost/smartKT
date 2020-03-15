import sys, os
from os.path import join as PJOIN
import pickle



def runForFolder(folder_name):
    for file in os.listdir(folder_name):
        abspath = PJOIN(folder_name, file)
        if os.path.isdir(abspath):
            runForFolder(abspath)
            continue
        (filename, ext) = os.path.splitext(abspath)
        if ext not in ['.c', '.C', '.cc', '.cpp', '.cxx', '.c++']:
            continue
        if REUSE and os.path.exists(filename+"_comments.xml"):
            print("Skipping: Already Exists: ", filename+"_comments.xml")
            continue
        os.system("python3 GenerateCommentsXMLForAFile.py " + abspath + " " + VOCAB_FILE + " " + PROBLEM_DOMAIN_FILE + " " + PROJECT_NAME)

if len(sys.argv) != 5:
    print("Give 4 arguments: PROJECT_SOURCE(containing the Clang), VOCAB_FILE, PROBLEM_DOMAIN_FILE, PROJECT_NAME - in this order")
    exit(-1)


# Fresh Run
REUSE = False

# Input arguments
PROJECT_SOURCE = os.path.abspath(sys.argv[1])
VOCAB_FILE = os.path.abspath(sys.argv[2])
PROBLEM_DOMAIN_FILE = os.path.abspath(sys.argv[3])
PROJECT_NAME = os.path.abspath(sys.argv[4])

os.chdir(os.path.dirname(os.path.abspath(__file__)))

runForFolder(PROJECT_SOURCE)
