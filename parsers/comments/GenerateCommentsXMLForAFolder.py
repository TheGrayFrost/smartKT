#!/usr/bin/env python3

# To use:
# python3 GenerateCommentsXMLForAFolder.py <project_folder> <output_folder> <vocab_file> <problem_domain_file> <project_name>

import sys, os
from os.path import join as PJOIN
import pickle
from concurrent.futures import ThreadPoolExecutor

MAX_WORKERS = 8

def getOutputLoc(path):
    relpath = path[path.index(PROJECT_NAME):]
    relpath = '/'.join(relpath.split('/')[1:])
    outpath = os.path.join(OUTPUTS_DIR, relpath)
    return PJOIN(outpath, os.path.splitext(outpath.split('/')[-1])[0])

def makeComGenCall(iopath):
    os.system(' '.join(['./GenerateCommentsXMLForAFile.py', iopath[0], iopath[1],
                     VOCAB_FILE, PROBLEM_DOMAIN_FILE, PROJECT_NAME]))

def runForFolder(folder_name, my_due=list(), first=False):
    for file in os.listdir(folder_name):
        abspath = PJOIN(folder_name, file)
        if os.path.isdir(abspath):
            runForFolder(abspath, my_due)
            continue
        (filename, ext) = os.path.splitext(abspath)
        if ext not in ['.c', '.C', '.cc', '.cpp', '.cxx', '.c++']:
            continue
        outprefix = getOutputLoc(abspath)
        if not os.path.exists(outprefix+'_clang.xml'):
            print('Skipping: No compile instructions: ' + abspath)
            continue
        if REUSE and os.path.exists(outprefix+'_comments.xml'):
            print('Skipping: Already Exists: ', outprefix+'_comments.xml')
            continue
        print ('Generating comments:', abspath)
        my_due.append((abspath, outprefix))

    if first:
        with ThreadPoolExecutor(max_workers = MAX_WORKERS) as pool:
            pool.map(makeComGenCall, my_due)

if len(sys.argv) != 6:
    print('Give 5 arguments: PROJECT_SOURCE, OUTPUTS_DIR, VOCAB_FILE, PROBLEM_DOMAIN_FILE, PROJECT_NAME - in this order')
    exit(-1)


if __name__ == '__main__':
    # Fresh Run
    REUSE = False

    # Input arguments
    PROJECT_SOURCE = os.path.abspath(sys.argv[1])
    OUTPUTS_DIR = os.path.abspath(sys.argv[2])
    VOCAB_FILE = os.path.abspath(sys.argv[3])
    PROBLEM_DOMAIN_FILE = os.path.abspath(sys.argv[4])
    PROJECT_NAME = sys.argv[5]

    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    runForFolder(PROJECT_SOURCE, first=True)
