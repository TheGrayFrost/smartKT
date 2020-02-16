#!/usr/bin/env python3

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
DWARFTOOL = 'dwxml.py'
COMBINER = 'ddx.py'
COMB_OUTPUTEXT = ' '.join([DWARF_EXTENSION, CLANG_EXTENSION, COMB_EXTENSION, OFFSET_EXTENSION])

INIT_FILE = 'init.sh'

path = os.path.abspath(sys.argv[1])
sppath = path.split('/')
project_name = (sppath[-1] if sppath[-1] != '' else sppath[-2])
outfolder = os.path.abspath('outputs/'+project_name)

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
        s += 'cmake -DCMAKE_BUILD_TYPE=Debug -DCMAKE_EXPORT_COMPILE_COMMANDS=1 ..\n'
        s += 'make -j$(nproc) VERBOSE=1 > make_log.txt\n'
        s += 'mkdir -p ' + outfolder + '\n'
        s += 'mv compile_commands.json ' + outfolder + '/\n'
        s += 'mv make_log.txt ' + outfolder + '/\n'
        with open(initfile, 'a') as f:
            f.write(s)

    os.system('chmod +x ' + initfile)
    os.system(initfile)

# This part is responsible for generating static outputs for code files.
def generate_static_info(path):
    global outfolder

    # Build the AST parser
    os.system('cd parsers && make clean && make all')

    # Get compile instructions
    # THIS PART WILL CHANGE FOR OTHER BUILD TOOLS
    with open(os.path.join(outfolder, 'compile_commands.json'), "r") as f:
        instrs = eval(f.read())

    for num, instr in enumerate(instrs):
        f = instr['file']
        mainfname = f[f.rfind('/')+1:f.rfind('.')]
        relpath = f[len(path)+1:]
        outpath = os.path.join(outfolder, relpath)
        os.system('mkdir -p ' + outpath)
        stripop = os.path.join(outpath, mainfname)
        os.system('cp ' + f + ' ' + os.path.join(outpath, f[f.rfind('/')+1:]))

        if DEBUG:
            print(stripop, fdep)

        print ('\n(%2d/%2d): Generating info for '%(num+1, len(instrs)) + relpath)

        try:
            # Select clang/Clang++ based on whether it is C/C++
            cmd = instr['command'].split(' ')
            clangv = 'clang++ -std=c++11'
            if f.split('.')[-1] == 'c':
                clangv = 'clang'

            # Get the objectfile
            objectfile = cmd[cmd.index('-o')+1]
            if not os.path.isabs(objectfile):
                objectfile = os.path.join(instr['directory'], objectfile)

            # Update the command to emit ast
            cmd[0] = clangv + ' -emit-ast'
            cmd[cmd.index('-o')+1] = mainfname + '.ast'
            os.system(' '.join(cmd))

            # Generate func, calls, ast
            for clangexe, output_extension in zip(CLANGTOOLS, CLANG_OUTPUTEXT):
                os.system ('parsers/' + clangexe + ' ' + mainfname + '.ast > ' + stripop + output_extension)

            # Move the ast into outputs
            os.system ('mv ' + mainfname + '.ast ' + outpath)

            print ('Clang Generated')

        except Exception as e:
            print(e)
            continue

        # direct object file parsing
        try:
            # generate dwarfdump for corresponding object file
            os.system('parsers/' + DWARFTOOL + ' ' + objectfile + ' -o ' + stripop + DWARF_EXTENSION)
            print ('Dwarfdump Generated')

            # combine dwarfdump and clang and get offset file
            os.system('parsers/' + COMBINER + ' ' + stripop + ' OFFSET ' + COMB_OUTPUTEXT)
            print ('Information combined')
        except Exception as e:
            print(e)
            continue

init(path)
generate_static_info(path)
