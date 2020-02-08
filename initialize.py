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
    # if os.path.isfile(initfile):
    #     with open(initfile, 'r') as f:
    #         u = ''.join(f.readlines())
    #     if u.rfind(s) == -1:
    #         print (u)
    #         print (s)

    os.system('chmod +x ' + initfile)
    os.system(initfile)

    # os.system('rm init.sh')
    # Copy the directory structure of the project, not needed anymore
    # s = 'set -x\n'
    # s += 'cd ' + path + '\n'
    # s += 'rm -rf build\n'
    # s += 'find . -type f \\( ' + ' -o '.join(['-name "*\\.'+x+'"' for x in FILE_EXTENSION]) + ' \\) > dirs.txt\n'
    # s += 'mv dirs.txt ' + outfolder + '/\n'
    # s += 'cd ' + outfolder + '\n'
    # s += 'xargs mkdir -p < dirs.txt\n'
    # with open('cpstruc.sh', 'w') as f:
    #     f.write(s)
    # os.system('chmod +x cpstruc.sh')
    # os.system('./cpstruc.sh')
    # os.system('rm cpstruc.sh')

def dependency_parser():
    # Parses the make log and presents the output in a format which can be accessed later
    global outfolder
    os.system('python parsers/project_parser.py ' + os.path.join(outfolder, 'make_log.txt'))
    os.system('mv dependencies.p ' + outfolder)

# This part is responsible for generating static outputs for code files.
def generate_static_info(path):

    # Read in the dependencies using pickle
    (dependencies, sourcefile, objectfile) = pickle.load(open(os.path.join(outfolder, 'dependencies.p'), 'rb'))
    
    # build the clang tool
    # s = 'set -x\n'
    # s += 'rm -f ast_parser || true\n'
    # s += 'g++ -std=c++11 -O3 `xml2-config --cflags --libs` -lclang ast2xml.cc -o ast_parser\n'
    # with open('parsers/astmaker.sh', 'w') as f:
    #     f.write(s)
    # os.system('chmod +x parsers/astmaker.sh')
    os.system('cd parsers && make clean && make all')
    # os.system('rm parsers/astmaker.sh')

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
            # print ('python parsers/clang_parser.py '+fdep+' > '+stripop + CLANG_OUTPUTEXT[0])
            # os.system('python parsers/clang_parser.py '+fdep+' > '+stripop + CLANG_OUTPUTEXT[0])
            for i, clangexe in enumerate(CLANGTOOLS):
                # print ('>>> parsers/' + clangexe + ' ' + mainfname + '.ast > ' + stripop + CLANG_OUTPUTEXT[i])
                os.system ('parsers/' + clangexe + ' ' + mainfname + '.ast > ' + stripop + CLANG_OUTPUTEXT[i])
            
            # print ('mv ' + mainfname + '.ast ' + outpath)
            os.system ('mv ' + mainfname + '.ast ' + outpath)

            print ('Clang Generated')
        
        # # clang_parser generates the clang XML, prints the function calls and function signatures in the files 
        # try:
        #     print('python parsers/clang_parser.py '+fdep+' '+CLANG_OUTPUTEXT)
        #     os.system('python parsers/clang_parser.py '+fdep+' '+CLANG_OUTPUTEXT)
        #     for EXT in [CLANG_EXTENSION, CALL_EXTENSION, SIGN_EXTENSION]:
        #         src_file = fstrip + EXT
        #         dest_file = stripop + EXT
        #         os.system('mv ' + src_file + ' ' + dest_file)
        #     print ('Clang Generated')
        except Exception as e:
            print(e)
            continue

        # direct object file parsing
        try:
            # generate dwarfdump for corresponding object file
            # print('>>> python dwarfdump -i ' + objectfile[f] + '> ' + stripop + '.dd')
            os.system('dwarfdump -i ' + objectfile[f] + '> ' + stripop + '.dd')
            # print('>>> python parsers/dwarfdump_parser.py '+ stripop + '.dd ' + DWARF_EXTENSION)
            os.system('python parsers/dwarfdump_parser.py '+ stripop + '.dd ' + DWARF_EXTENSION)
            print ('Dwarfdump Generated')
            # combine dwarfdump and clang and get offset file
            print('>>> python parsers/ddx.py ' + stripop + ' OFFSET ' + DWARF_OUTPUTEXT)
            os.system('python parsers/ddx.py ' + stripop + ' OFFSET ' + DWARF_OUTPUTEXT)
            print ('Information combined')
        except Exception as e:
            print(e)
            continue

        # print ('(%2d/%2d): Generated info for '%(num+1, len(objectfile)) + relpath + '\n')

    ''' 
        to use the C++ clang tool


    build the clang tool
    s = 'set -x\n'
    s += 'rm -f ast_parser || true\n'
    s += 'g++ -std=c++11 -O3 `xml2-config --cflags --libs` -lclang ast_parser.cc -o ast_parser\n'
    with open('parsers/astmaker.sh', 'w') as f:
        f.write(s)
    os.system('chmod +x parsers/astmaker.sh')
    os.system('cd parsers && ./astmaker.sh')
    os.system('rm parsers/astmaker.sh')

            clangv = 'clang++ -std=c++11'
            if f.split('.')[-1] == 'c':
                clangv = 'clang'
            os.system(clangv + ' -emit-ast ' + fdep)
            mainfname = f[f.rfind('/')+1:f.rfind('.')]
            relpath = f[len(path)+1:f.rfind('.')]
            print ('parsers/ast_parser ' + outast + ' mycur ' + CLANG_INPUTEXT)
            exit()
            os.system('parsers/ast_parser ' + mainfname + '.ast ' + mainfname + ' ' + CLANG_INPUTEXT)
    '''


        # Generate and copy the preprocess file
        # try:
        #     os.system('python parsers/preprocessor_extractor.py '+f)
        #     src_file = f.split('.')[0] + '_preprocess.csv'
        #     dest_file = '/'.join(f.split('/')[f.split('/').index(proj_name):]).split('.')[0] + '_preprocess.csv'
        #     os.system('mv ' + src_file + ' ' + dest_file)
        # except Exception as e:
        #     print(e)
        #     continue

        # Get PYGCCXML output
        # try:
        #     s = 'set -x\n'
        #     s += 'cd parsers/pygccxml' + '\n'
        #     s += 'python main.py ' + f + ' '
        #     for d in dependencies[f]:
        #         s += d + ' '
        #     s += '\n'
        #     src_file = f.split('.')[0] + '_pygccxml.xml'
        #     dest_file = '/'.join(f.split('/')[f.split('/').index(proj_name):]).split('.')[0] + '_pygccxml.xml'
        #     s += 'cd '+ os.getcwd() + '\n'
        #     s += 'mv ' + src_file + ' ' + dest_file
        #     with open('pygcc.sh', 'w') as fl:
        #         fl.write(s)
        #     os.system('chmod +x pygcc.sh')
        #     os.system('./pygcc.sh')
        #     os.system('rm pygcc.sh')
        # except:
        #     continue

        # Combine files
        # try:
        #     combine(dest_file.split('.')[0][:-8]+'combined.xml', dest_file, f)
        # except:
        #     continue

# def combine(clangf, pygccf, cppfile):
#     # This function combines the Clang output and PYGCCXML output into one XML
#     try:
#         ctree = ET.parse(clangf)
#         croot = ctree.getroot()
#     except:
#         croot = Element('CLANG')
#     try:
#         ptree = ET.parse(pygccf)
#         proot = ptree.getroot()
#     except:
#         proot = Element('PYGCCXML')

#     root = Element('file')
#     root.set('name', cppfile)
#     root.append(croot)
#     root.append(proot)
#     xmlstr = minidom.parseString(ET.tostring(root)).toprettyxml(indent='   ')
#     with open(clangf, 'w') as f:
#         f.write(xmlstr)

path = os.path.abspath(sys.argv[1])
sppath = path.split('/')
project_name = (sppath[-1] if sppath[-1] != '' else sppath[-2])
outfolder = os.path.abspath('outputs/'+project_name)
init(path)
dependency_parser()
generate_static_info(path)
