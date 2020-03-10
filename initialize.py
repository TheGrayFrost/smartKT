#!/usr/bin/env python3

# To use:
# python initialize.py <path to project> [<optional output folder name>]
# The last name in the path is assumed the project name

import sys, os, pickle
from xml.etree.ElementTree import Element, SubElement
from xml.etree import ElementTree as ET
from xml.dom import minidom

from concurrent.futures import ThreadPoolExecutor
from parsers.funcs import emit_funcargs

DEBUG = False

MAX_WORKERS = 8

# input files and extensions
C_EXTENSION = ['c', 'C']
CXX_EXTENSION = ['cc', 'cpp', 'cxx', 'c++']
FILE_EXTENSION = C_EXTENSION + CXX_EXTENSION
INIT_FILE = 'init.sh'

FOLDER = 'outputs'

# tools
CLANGTOOLS = ['ast2xml', 'calls'] # , 'funcs']
# SOURCE_EXTENSION = {'ast2xml': '.ast', 'calls': '.ast', 'funcs': '_clang.xml'}
# CLANGTOOLS[0] = 'clang_parser.py'
DWARFTOOL = 'dwxml.py'
COMBINER = 'ddx.py'

# output extensions
CLANG_EXTENSION = '_clang.xml'
DWARF_EXTENSION = '_dd.xml'
COMB_EXTENSION = '_comb.xml'
CALL_EXTENSION = '.calls'
SIGN_EXTENSION = '.funcargs'
OFFSET_EXTENSION = '.offset'
CLANG_OUTPUTEXT = [CLANG_EXTENSION, CALL_EXTENSION] # , SIGN_EXTENSION]
COMB_OUTPUTEXT = ' '.join([DWARF_EXTENSION, CLANG_EXTENSION, COMB_EXTENSION, OFFSET_EXTENSION])

path = os.path.abspath(sys.argv[1])

if (len(sys.argv) == 3):
    FOLDER = sys.argv[2]

sppath = path.split('/')
project_name = (sppath[-1] if sppath[-1] != '' else sppath[-2])
outfolder = os.path.abspath(os.path.join(FOLDER,project_name))

def init(path):
    # This function builds the project and in that process gets the make log file
    # Build the project
    initfile = os.path.join(path, INIT_FILE)
    s = 'set -x\n'
    s += 'cd ' + path + '\n'
    s += 'rm -rf build\n'
    s += 'mkdir build\n'
    s += 'cd build\n'
    s += 'cmake -DCMAKE_BUILD_TYPE=Debug -DCMAKE_EXPORT_COMPILE_COMMANDS=1 ..\n'
    s += 'make -j$(nproc) VERBOSE=1 > make_log.txt\n'
    s += 'mkdir -p ' + outfolder + '\n'
    s += 'mv compile_commands.json ' + outfolder + '/\n'
    s += 'mv make_log.txt ' + outfolder + '/\n'
    s += 'rm ' + initfile + '\n'
    with open(initfile, 'w') as f:
        f.write(s)

    os.system('chmod +x ' + initfile)
    os.system(initfile)

# This part is responsible for generating static outputs for code files.
def generate_static_info(path):
    global outfolder

    # Build the AST parser
    os.system('cd parsers && make all')

    # Get compile instructions
    # THIS PART WILL CHANGE FOR OTHER BUILD TOOLS
    with open(os.path.join(outfolder, 'compile_commands.json'), "r") as f:
        instrs = eval(f.read())

    # for num, instr in enumerate(instrs, 1):
    def generate_static_info_for_tu(arg) :
        num, instr = arg
        f = instr['file']
        mainfname = f[f.rfind('/')+1:f.rfind('.')]
        relpath = f[len(path)+1:]
        outpath = os.path.join(outfolder, relpath)
        os.system('mkdir -p ' + outpath)
        stripop = os.path.join(outpath, mainfname)
        os.system('cp ' + f + ' ' + os.path.join(outpath, f[f.rfind('/')+1:]))

        if DEBUG:
            print(stripop, f)

        print ('\n(%2d/%2d): Generating info for ' % (num, len(instrs)) + relpath + '\n', end='')

        logstr = '\n(%2d/%2d): Generated info for ' % (num, len(instrs)) + relpath + '\n'

        try:
            # Select clang/Clang++ based on whether it is C/C++
            cmd = instr['command'].split(' ')
            clangv = 'clang++ -std=c++11'
            if f.split('.')[-1] in C_EXTENSION:
                clangv = 'clang'

            # Get the objectfile
            objectfile = cmd[cmd.index('-o')+1]
            if not os.path.isabs(objectfile):
                objectfile = os.path.join(instr['directory'], objectfile)

            # Update the command to emit ast
            cmd[0] = clangv + ' -emit-ast'
            cmd[cmd.index('-o')+1] = mainfname + '.ast'
            os.system(' '.join(cmd))

            # Generate func, calls, xml - file number prepended to all nodeids to make unique
            for clangexe, output_extension in zip(CLANGTOOLS, CLANG_OUTPUTEXT):
                os.system (' '.join(['parsers/'+clangexe, str(num), 
                    mainfname+'.ast', '>', stripop + output_extension]))
                logstr += ('output :' + stripop + output_extension + '\n')

            emit_funcargs(stripop + CLANG_EXTENSION, stripop + SIGN_EXTENSION)
            logstr += ('output :' + stripop + output_extension + '\n')

            # Move the ast into outputs
            os.system ('mv ' + mainfname + '.ast ' + outpath)
            logstr += ('Clang output generated ' + outpath + '\n')

        except Exception as e:
            print('\n'.join([relpath, logstr, e]), end='', file=sys.stderr)
            return # continue

        # direct object file parsing
        try:
            # generate dwarfdump for corresponding object file
            os.system('parsers/' + DWARFTOOL + ' ' + objectfile + ' -q -o ' + stripop + DWARF_EXTENSION)
            logstr += ('Dwarfdump Generated : parsers/' + DWARFTOOL + ' ' +
                objectfile + ' -q -o ' + stripop + DWARF_EXTENSION)
            # print ('Dwarfdump Generated')

            # combine dwarfdump and clang and get offset file
            os.system('parsers/' + COMBINER + ' ' + stripop + ' OFFSET ' + COMB_OUTPUTEXT)
            logstr += ('Information combined : parsers/' + COMBINER + ' ' +
                stripop + ' OFFSET ' + COMB_OUTPUTEXT + '\n')
            # print ('Information combined')
        except Exception as e:
            print('\n'.join([relpath, logstr, e]), end='', file=sys.stderr)
            return # continue
        print('\n'.join([relpath, logstr]), end='')

    with ThreadPoolExecutor(max_workers = MAX_WORKERS) as pool :
        pool.map( generate_static_info_for_tu, enumerate(instrs, 1) )


init(path)
generate_static_info(path)
