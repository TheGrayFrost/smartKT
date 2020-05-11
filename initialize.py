#!/usr/bin/env python3

# To use:
# python3 initialize.py <path to project> [<optional output folder name>]

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
# CLANGTOOLS = ['ast2xml', 'calls']
DWARFTOOL = 'dwxml.py'
COMBINER = 'saved_ddx.py'
PROJPARSER = 'project_parser.py'

# output extensions
CLANG_EXTENSION = '_clang.xml'
DWARF_EXTENSION = '_dd.xml'
COMB_EXTENSION = '_comb.xml'
CALL_TEMP_EXTENSION = '.calls.temp'
CALL_FINAL_EXTENSION = '.calls.tokens'
SIGN_EXTENSION = '.funcargs'
OFFSET_EXTENSION = '.offset'
# CLANG_OUTPUTEXT = [CLANG_EXTENSION, CALL_EXTENSION] # , SIGN_EXTENSION]
COMB_OUTPUTEXT = ' '.join([DWARF_EXTENSION, CLANG_EXTENSION, COMB_EXTENSION, OFFSET_EXTENSION])

path = os.path.abspath(sys.argv[1])

if (len(sys.argv) > 2):
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
    # s += 'cmake -DCMAKE_BUILD_TYPE=Debug -DCMAKE_EXPORT_COMPILE_COMMANDS=1 ..\n'
    s += 'cmake -DCMAKE_BUILD_TYPE=Debug ..\n'
    s += 'make -j$(nproc) VERBOSE=1 > make_log.txt\n'
    s += 'mkdir -p ' + outfolder + '\n'
    # s += 'mv compile_commands.json ' + outfolder + '/\n'
    s += 'mv make_log.txt ' + outfolder + '/\n'
    s += 'rm ' + initfile + '\n'
    with open(initfile, 'w') as f:
        f.write(s)

    os.system('chmod +x ' + initfile)
    os.system(initfile)

# This part is responsible for generating static outputs for code files.
def generate_static_info(path):
    global outfolder

    # Build the clang tools
    if DEBUG:
        print ('CMD: ', 'cd parsers && make all')
    os.system('cd parsers && make all')

    # Get compile instructions using project_parser.py
    # THIS PART WILL CHANGE FOR OTHER BUILD TOOLS
    if DEBUG:
        print ('CMD: ', ' '.join(['parsers/' + PROJPARSER, os.path.join(outfolder, 'make_log.txt'),
                    os.path.join(path, 'build'), os.path.join(outfolder, 'dependencies.p')]))
    os.system(' '.join(['parsers/' + PROJPARSER, os.path.join(outfolder, 'make_log.txt'),
                    os.path.join(path, 'build'), os.path.join(outfolder, 'dependencies.p')]))

    with open(os.path.join(outfolder, 'dependencies.p'), 'rb') as depf:
        dependencies = pickle.load(depf)
    compile_instrs = dependencies['compile_instrs']

    # for num, instr in enumerate(instrs, 1):
    def generate_static_info_for_tu(arg):
        num, fname = arg
        instr = compile_instrs[fname]
        f = instr['file']

        # if file's full path is project/exp/src/alpha.cc
        # path would be projects/exp
        # outfolder will be outputs/exp
        # mainfname will be alpha
        # relpath will be src/alpha.cc
        # i.e. the folder name alpha.cc shall contain files generated for the file alpha.cc
        # outpath, thus will be outputs/exp/src/alpha.cc
        # stripop will be: outputs/exp/src/alpha.cc/alpha
        # so, all extensions are appended to stripop, eg: outputs/exp/src/alpha.cc/alpha_clang.xml
        mainfname = f[f.rfind('/')+1:f.rfind('.')]
        relpath = f[len(path)+1:]
        outpath = os.path.join(outfolder, relpath)
        if DEBUG:
            print ('CMD: ', 'mkdir -p ' + outpath)
            print ('CMD: ', 'cp ' + f + ' ' + os.path.join(outpath, f[f.rfind('/')+1:]))
        os.system('mkdir -p ' + outpath)
        stripop = os.path.join(outpath, mainfname)
        os.system('cp ' + f + ' ' + os.path.join(outpath, f[f.rfind('/')+1:]))

        if DEBUG:
            print(stripop, f)

        if not (relpath.split('.')[-1] in C_EXTENSION or relpath.split('.')[-1] in CXX_EXTENSION):
            print('\n(%2d/%2d): Ommiting info (non C/C++) for '%(num, len(compile_instrs)) + relpath)
            return # continue

        print ('\n(%2d/%2d): Generating info for ' % (num, len(compile_instrs)) + relpath + '\n', end='')

        logstr = '\n(%2d/%2d): Generated info for ' % (num, len(compile_instrs)) + relpath + '\n'

        try:
            # Select clang/clang++ based on whether it is C/C++
            cmd = instr['command'].split(' ')
            clangv = 'clang++ -std=c++11'
            if f.split('.')[-1] in C_EXTENSION:
                clangv = 'clang'

            # Get the objectfile
            objectfile = instr.get('object', None)
            if objectfile is None:
                objectfile = cmd[cmd.index('-o')+1]
            if not os.path.isabs(objectfile):
                objectfile = os.path.abspath(os.path.join(instr['directory'], objectfile))

            # Update the command to emit ast
            cmd[0] = clangv + ' -emit-ast'
            cmd[cmd.index('-o')+1] = mainfname + '.ast'

            # Remove flags that cause errors
            cmd = ' '.join([x for x in cmd if x not in ['-flifetime-dse=1']])

            if DEBUG:
                print ('CMD: ', cmd)
            os.system(cmd)

            # Generate clang xml & .calls.temp - file number prepended to all nodeids to make unique
            if DEBUG:
                print ('CMD: ', ' '.join(['parsers/ast2xml', str(num), f, mainfname+'.ast',
                            stripop+CALL_TEMP_EXTENSION, stripop+CLANG_EXTENSION ]))
            os.system(' '.join(['parsers/ast2xml', str(num), f, mainfname+'.ast',
                            stripop+CALL_TEMP_EXTENSION, stripop+CLANG_EXTENSION ]))
            logstr += ('output :' + stripop + CLANG_EXTENSION + '\n')
            logstr += ('output :' + stripop + CALL_TEMP_EXTENSION + '\n')

            # Add tokens to .calls.temp and produces .calls.tokens
            if DEBUG:
                print ('CMD: ', ' '.join(['parsers/calls', 
                    stripop+CALL_TEMP_EXTENSION, stripop+CALL_FINAL_EXTENSION]))
            os.system(' '.join(['parsers/calls', stripop+CALL_TEMP_EXTENSION, stripop+CALL_FINAL_EXTENSION]))
            logstr += ('output :' + stripop + CALL_FINAL_EXTENSION + '\n')

            # Create .funcargs
            if DEBUG:
                print ('CMD: ', f'./func.py {stripop + CLANG_EXTENSION} {stripop + SIGN_EXTENSION}')
            emit_funcargs(stripop + CLANG_EXTENSION, stripop + SIGN_EXTENSION)
            logstr += ('output :' + stripop + SIGN_EXTENSION + '\n')

            # Move the ast into outputs
            if DEBUG:
                print ('CMD: ', 'mv ' + mainfname + '.ast ' + outpath)
            os.system ('mv ' + mainfname + '.ast ' + outpath)
            logstr += ('Clang output generated: ' + outpath + '\n')

        except Exception as e:
            print('\n'.join([relpath, logstr, e]), end='', file=sys.stderr)
            return # continue

        # direct object file parsing
        try:
            # generate dwarfdump for corresponding object file
            os.system('parsers/' + DWARFTOOL + ' ' + objectfile + ' -q -o ' + stripop + DWARF_EXTENSION)
            logstr += 'Dwarfdump Generated : '
            if DEBUG:
                print('CMD: ', 'parsers/'+ DWARFTOOL+' '+objectfile+' -q -o '+stripop+DWARF_EXTENSION)
            logstr += stripop + DWARF_EXTENSION + '\n'
            # print ('Dwarfdump Generated')

            # combine dwarfdump and clang and get offset file
            os.system('parsers/' + COMBINER + ' ' + stripop + ' OFFSET ' + COMB_OUTPUTEXT)
            logstr += 'Information combined : '
            if DEBUG:
                print('CMD: ', 'parsers/'+COMBINER+' '+stripop+' OFFSET '+COMB_OUTPUTEXT)
            logstr += '\n' + '\n'.join([stripop + myext for 
                myext in [COMB_EXTENSION, OFFSET_EXTENSION]]) + '\n\n'
             # print ('Information combined')
        except Exception as e:
            print('\n'.join([relpath, logstr, e]), end='', file=sys.stderr)
            return # continue
        if DEBUG:
            print('\n'.join(['\nGenerating for: ' + relpath, logstr]), end='')
        else:
            print(logstr, end='')

    # Run the generate_static_info_for_tu function for each translation unit in parallel.
    with ThreadPoolExecutor(max_workers = MAX_WORKERS) as pool :
        pool.map(generate_static_info_for_tu, enumerate(compile_instrs, 1))


# Get the pyelftools library if not already present.
if not os.listdir(os.path.join('parsers', 'pyelftools')):
    os.system('cd parsers && git clone https://github.com/eliben/pyelftools.git')
init(path)
generate_static_info(path)
