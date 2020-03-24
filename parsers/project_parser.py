#!/usr/bin/env python3

'''
This program finds the linking information (static and dynamic)
and stores in dependencies.p (pickle format)
'''

import re, os, sys, pickle
import subprocess

DEBUG = False

#[TODO]: Support more compilers, for projects that are multi-lingual (NOT A PRIORITY)
# The compiler used by the project.
# These are the default selections for cmake
# On the server, devtoolset gcc '/opt/rh/devtoolset-8/root/usr/bin/cc' also ends with same phrase
C_COMPILER = '/usr/bin/cc '
CXX_COMPILER = '/usr/bin/c++ '

# C_EXTENSION = '.c '
FILE_EXTENSION = ['c', 'C', 'cc', 'cpp', 'cxx', 'c++']

#[TODO]: Implement support for other archivers (NOT A PRIORITY)
STATIC_ARCHIVER = '/usr/bin/ar '

CHANGE_DIRECTORY_CMD = 'cd '

# filename: The make_log.txt file, which contains the verbose output of the build
# We try to extract various dependencies using this file
filename = sys.argv[1]

with open(filename, 'r') as f:
    data = f.readlines()

'''
We open the make_log.txt file and try to find 3 types of essential commands:
1. CXX_COMMANDS: These commands including compiling and linking instructions
                (line num, last cd command, cxx command)
2. CD_COMMANDS: We use these commands to keep track of the directory of the files
                we are compiling/linking
                (line num, cd command)
3. AR_COMMANDS: Archiving commands. Combine multiple object files into one.
                (line num, last cd command, ar command)

The algorithm is pretty simple. The way CMake generates the Makefile and the way
Makefile builds objects and binaries, is very standard, making the parsing
straightforward. We are just looking for the occurance of the three commands
mentioned above, and store relevant information in lists.
'''

cxx_cmds = []
cd_cmds = []
static_link_cmds = []
cur_path = sys.argv[2]

# Proper path takes care of .. and .
def properPathJoin(base, next):
    stack = base.split('/')
    toAppend = next.strip().split('/')
    for t in toAppend:
        if t == "..":
            stack = stack[:-1]
        elif t == ".":
            continue
        else:
            stack.append(t)
    return '/'.join(stack)

def searchFile(filePath):
    file = filePath.split('/')[-1]
    abspath = subprocess.check_output("find "+ sys.argv[2] +" -name "+file+" | grep "+filePath, shell=True).decode('utf-8').strip()
    if not os.path.isabs(abspath):
        abspath = properPathJoin(base, abspath)
    if not os.path.exists(abspath) or not os.path.isabs(abspath):
        print("Incorrect file: " + abspath)
    return abspath

for line_num, x in enumerate(data):
    # expects only one cd in any command - true for cmake generated and any other sensible make file
    if CHANGE_DIRECTORY_CMD in x:
        temp_ls = x.split()
        cd_index = temp_ls.index(CHANGE_DIRECTORY_CMD.strip())

        # check for relative cd's... will see if useful with libpng @VISHESH
        cd_path = temp_ls[cd_index+1]
        if not os.path.isabs(cd_path):
            cd_path = os.path.join(cur_path, cd_path)
        cd_path = os.path.abspath(cd_path)
        cur_path = cd_path
        cd_cmds.append(cd_path)

        # again, expects only one cxx in any command - true for cmake generated and any other sensible make file
        if CXX_COMPILER in x:
            idx = 0
            for i, word in enumerate(temp_ls):
                if CXX_COMPILER.strip() in word:
                    idx = i
                    break
            cxx_cmds.append((cd_cmds[-1], ' '.join(temp_ls[idx:])))
        if C_COMPILER in x:
            idx = 0
            for i, word in enumerate(temp_ls):
                if C_COMPILER.strip() in word:
                    idx = i
                    break
            cxx_cmds.append((cd_cmds[-1], ' '.join(temp_ls[idx:])))

    # again, expects only one cxx in any command - true for cmake generated and any other sensible make file
    elif CXX_COMPILER in x:
        req_cmd = x[x.index(CXX_COMPILER):]
        req_cmd = req_cmd.split('&&')[0].strip()
        cxx_cmds.append((cd_cmds[-1], req_cmd))
    elif C_COMPILER in x:
        req_cmd = x[x.index(C_COMPILER):]
        req_cmd = req_cmd.split('&&')[0].strip()
        cxx_cmds.append((cd_cmds[-1], req_cmd))
    elif STATIC_ARCHIVER in x:
        static_link_cmds.append((cd_cmds[-1], x.strip()))

dependencies = {}
dependencies["compile_instrs"] = {}
compile_instrs = dependencies["compile_instrs"]

# For this small project, it is sufficient to print this
for path, data in cxx_cmds: # these commands create some executable
    cwd = path
    d = data.split()

    # get the output file name
    if '-o' in d:
        eidx = d.index('-o')+1
        executable = d[d.index('-o')+1]
        if not os.path.isabs(executable):
            executable = searchFile(executable)
        executable = os.path.abspath(executable)
        dependencies[executable] = set()

    # an object creation command
    if '-c' in d:
        # expecting one direct object per file, true for cmake build system
        # collect all files with the expected extensions
        for word in d:
            j = word.split('.')[-1]
            if j in FILE_EXTENSION:
                filename = word
                if DEBUG:
                    print (filename)
                break
        if not os.path.isabs(filename):
            # SRC files are generally mentioned with absolute path
            filename = os.path.join(cwd, filename)
        filename = os.path.abspath(filename)
        dependencies[executable] = filename
        compile_instrs[filename] = {
            'command': data,
            'directory': cwd,
            'file': filename,
            'object': executable
        }

    else:
        # must be a linking instruction
        rdynamic_lib = []   # allows for multiple rdynamic links
        linker_opts = ['-rpath', '.']   # by default you look in cwd... i don't completely understand this...
                                        # the manual says you shouldn't but expt run otherwise
        for idx, x in enumerate(d):
            if idx != eidx:
                if x.find('-Wl') != -1:
                    linker_opts += x.split(',')[1:]
                elif x[-2:] == '.o' or x[-2:] == '.a':
                    if not os.path.isabs(x):
                        x = searchFile(x)
                    dependencies[executable].add(os.path.abspath(x))
                elif x.find('.so') != -1:
                    rdynamic_lib.append(x)

        # don't have the absolute path just yet, need to search over rpaths
        # in cmake generated rdynamic links, rpath is passed to the linker as an argument to -Wl
        # so we need to find all options passed via -Wl
        rpaths = [linker_opts[i+1] for i, x in enumerate(linker_opts) if x == '-rpath']
        rpaths = [os.path.abspath(u) if os.path.isabs(u) else os.path.join(cwd, u) for u in rpaths]

        # look for libraries in the rdynamic lookup paths like the linker would have
        for rlib in rdynamic_lib:
            for path in rpaths:
                lib_abspath = os.path.abspath(os.path.join(path, rlib))
                if os.path.exists(lib_abspath):
                    dependencies[executable].add(lib_abspath)
                    break

# This is for libraries. Libraries are created by combining object files
for path, data in static_link_cmds:
    cwd = path
    d = data.strip().split()
    # qc is specific to cmake... ar options order guarantees that archive is the third element (2nd being the options)
    libfile = d[2]       
    if not os.path.isabs(libfile):
        properPathJoin(cwd, libfile)
    dependencies[libfile] = set()
    for x in d[3:]:
        if x[-2:] == '.o' or x[-2:] == '.a' : # added check for archives getting linked to bigger archives
            if not os.path.isabs(x):
                x = searchFile(x)
            dependencies[libfile].add(os.path.abspath(x))

pickle.dump(dependencies, open(sys.argv[3], 'wb'))
