# To use:
# python initialize.py <path to project>
# The last name in the path is assumed the project name

import sys, os, pickle
from xml.etree.ElementTree import Element, SubElement
from xml.etree import ElementTree as ET
from xml.dom import minidom

DEBUG = False

FILE_EXTENSION = ['c', 'C', 'cc', 'cpp', 'cxx', 'c++']
CLANG_EXTENSION = '_clang.xml'
DWARF_EXTENSION = '_dd.xml'
COMB_EXTENSION = '_comb.xml'
CALL_EXTENSION = '.calls'
SIGN_EXTENSION = '.funcargs'
OFFSET_EXTENSION = '.offset'
CLANGTOOLS = ['ast2xml', 'calls', 'funcs']
CLANG_OUTPUTEXT = [CLANG_EXTENSION, CALL_EXTENSION, SIGN_EXTENSION]
DWARFTOOL = ['ddx.py']
DWARF_OUTPUTEXT = ' '.join([DWARF_EXTENSION, CLANG_EXTENSION, COMB_EXTENSION, OFFSET_EXTENSION])

INIT_FILE = 'init.sh'

def init(path):
    # This function builds the project and in that process gets the make log file
    # Build the project
    initfile = os.path.join(path, INIT_FILE)
    s = ''
    if not os.path.isfile(initfile):
        s += 'set -x\n'
        s += 'cd ' + path + '\n'
        s += 'rm -rf build\n'
        s += 'mkdir build\n'
        s += 'cd build\n'
        s += 'cmake -DCMAKE_BUILD_TYPE=Debug ..\n'
        s += 'make -j$(nproc) VERBOSE=1 > make_log.txt\n'
        s += 'mkdir -p ' + outfolder + '\n'
        s += 'mv make_log.txt ' + outfolder + '/\n'
        with open(initfile, 'a') as f:
            f.write(s)

    os.system('chmod +x ' + initfile)
    os.system(initfile)

def dependency_parser():
    # Parses the make log and presents the output in a format which can be accessed later
    global outfolder
    os.system('python parsers/project_parser.py ' + os.path.join(outfolder, 'make_log.txt'))
    os.system('mv dependencies.p ' + outfolder)

# This part is responsible for generating static outputs for code files.
def generate_static_info(path):

    # Read in the dependencies using pickle
    (dependencies, sourcefile, objectfile) = pickle.load(open(os.path.join(outfolder, 'dependencies.p'), 'rb'))

    os.system('cd parsers && make clean && make all')

    # For all files that generate a direct object
    for num, f in enumerate(objectfile):
        # create the file + includes for clang
        fdep = f
        for d in dependencies[f]:
            fdep += ' ' + d

        fstrip = f[:f.rfind('.')]
        mainfname = f[f.rfind('/')+1:f.rfind('.')]
        relpath = f[len(path)+1:]
        outpath = os.path.join(outfolder, relpath)
        os.system('mkdir -p ' + outpath)
        stripop = os.path.join(outpath, mainfname)
        os.system('cp ' + f + ' ' + os.path.join(outpath, f[f.rfind('/')+1:]))

        if DEBUG:
            print(stripop, fdep)

        print ('\n(%2d/%2d): Generating info for '%(num+1, len(objectfile)) + relpath)

        try:
            clangv = 'clang++ -std=c++11'
            if f.split('.')[-1] == 'c':
                clangv = 'clang'
            os.system(clangv + ' -emit-ast ' + fdep)
            for i, clangexe in enumerate(CLANGTOOLS):
                os.system ('parsers/' + clangexe + ' ' + mainfname + '.ast > ' + stripop + CLANG_OUTPUTEXT[i])

            os.system ('mv ' + mainfname + '.ast ' + outpath)

            print ('Clang Generated')

        except Exception as e:
            print(e)
            continue

        # direct object file parsing
        try:
            # generate dwarfdump for corresponding object file
            os.system('dwarfdump -i ' + objectfile[f] + '> ' + stripop + '.dd')
            os.system('python parsers/dwarfdump_parser.py '+ stripop + '.dd ' + DWARF_EXTENSION)
            print ('Dwarfdump Generated')

            # combine dwarfdump and clang and get offset file
            os.system('python parsers/ddx.py ' + stripop + ' OFFSET ' + DWARF_OUTPUTEXT)
            print ('Information combined')
        except Exception as e:
            print(e)
            continue


path = os.path.abspath(sys.argv[1])
sppath = path.split('/')
project_name = (sppath[-1] if sppath[-1] != '' else sppath[-2])
outfolder = os.path.abspath('outputs/'+project_name)
init(path)
dependency_parser()
generate_static_info(path)
