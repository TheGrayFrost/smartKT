import sys, os
from os.path import join as PJOIN
import pickle


def getOutputLoc(path):
    relpath = path[path.index(PROJECT_NAME):]
    outpath = os.path.join(OUTPUTS_DIR, relpath)
    return PJOIN(outpath, os.path.splitext(outpath.split('/')[-1])[0])

def runForFolder(folder_name):
    for file in os.listdir(folder_name):
        abspath = PJOIN(folder_name, file)
        if os.path.isdir(abspath):
            runForFolder(abspath)
            continue
        (filename, ext) = os.path.splitext(abspath)
        if ext not in ['.c', '.C', '.cc', '.cpp', '.cxx', '.c++']:
            continue
        outprefix = getOutputLoc(abspath)
        if REUSE and os.path.exists(outprefix+"_comments.xml"):
            print("Skipping: Already Exists: ", outprefix+"_comments.xml")
            continue
        os.system("python3 GenerateCommentsXMLForAFile.py " + abspath + " " + outprefix + \
            " " + VOCAB_FILE + " " + PROBLEM_DOMAIN_FILE + " " + PROJECT_NAME)

if len(sys.argv) != 6:
    print("Give 5 arguments: PROJECT_SOURCE, OUTPUTS_DIR, VOCAB_FILE, PROBLEM_DOMAIN_FILE, PROJECT_NAME - in this order")
    exit(-1)


# Fresh Run
REUSE = False

# Input arguments
PROJECT_SOURCE = os.path.abspath(sys.argv[1])
OUTPUTS_DIR = os.path.abspath(sys.argv[2])
VOCAB_FILE = os.path.abspath(sys.argv[3])
PROBLEM_DOMAIN_FILE = os.path.abspath(sys.argv[4])
PROJECT_NAME = os.path.abspath(sys.argv[5])

os.chdir(os.path.dirname(os.path.abspath(__file__)))

runForFolder(PROJECT_SOURCE)
