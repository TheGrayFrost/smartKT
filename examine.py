#!/usr/bin/env python3

# Before you can use, specify the details in config.txt file
# To use:
# python3 examine.py <json_file>

'''
Dynamic information is available for executables only. So we combine all static
information from multiple CPP files into one XML and then add the dynamic_information
into the XML. For more details, read the report.
'''

import sys, pickle, os
from xml.etree.ElementTree import Element, SubElement
from xml.etree import ElementTree as ET
from xml.dom import minidom
from collections import defaultdict
import json

import parsers.imp_ddx as ddx
import parsers.vcs as vcs

from parsers.uniquify import uniquify

# For debug, set true
DEBUG = False

# tools
PROJPARSER = 'project_parser.py'
DWARFTOOL = 'dwxml.py'
COMBINER = 'ddx.py'

# i/o extensions
DWARF_EXTENSION = '_dd.xml'
COMB_EXTENSION = '_comb.xml'
CALL_EXTENSION = '.calls.tokens'
SIGN_EXTENSION = '.funcargs'
OFFSET_EXTENSION = '.offset'
ADDRESS_EXTENSION = '.address'
SYMTAB_EXTENSION = '.symtab'
TEMP_EXTENSION = '.temp.xml'
FINAL_FILE = 'final'
STATIC_EXTENSION = '_static.xml'
DYNAMIC_EXTENSION = '_dynamic.xml'
COMMENTS_EXTENSION = "_comments.xml"
VCS_EXTENSION = "_vcs.xml"

# FOLDERS
COMMENTS_FOLDER = os.path.join('parsers', 'comments')
PROJECTS_FOLDER = 'projects'
OUTPUTS_FOLDER = 'outputs'

if len(sys.argv) > 2:
    OUTPUTS_FOLDER = sys.argv[2]

# DOMAINS TO RUN
CALLSTATIC = False
CALLDYN = False
CALLCOMM = True
CALLVCS = False


# Rewriting to be able to run multiple tests simultaneously
executable, test_input, execstrip = None, None, None
origpath, project_name, outfolder = None, None, None
foutfolder, dependencies = None, None

def combine_all_clang(depmap):
    CURFINALFILE = os.path.join(foutfolder, FINAL_FILE)

    # create joint info files
    for EXT in [CALL_EXTENSION, SIGN_EXTENSION, OFFSET_EXTENSION, STATIC_EXTENSION]:
        os.system('> ' + os.path.join(foutfolder, CURFINALFILE+EXT))

    # list of exe/so roots
    rootlist = []

    # list of .address files
    address_files = []

    headerWrite = [False, False, False]
    for numexe, (exe, flist) in enumerate(depmap):
        exenamestrip = exe[exe.rfind('/')+1:]
        exeoutfolder = os.path.join(foutfolder, exenamestrip)
        exestrip = os.path.join(exeoutfolder, exenamestrip)
        os.system('mkdir -p ' + exeoutfolder)
        print ('\nGenerating info for ' + exenamestrip)

        # generate dwarfdump and its xml for the so or the main executable
        os.system('parsers/'+DWARFTOOL+' '+exe+' -q -o '+exestrip+DWARF_EXTENSION)
        print ('Created dwarfdump for ' + exenamestrip)

        # create map from the dwarf xml
        dtree = ET.parse(exestrip+DWARF_EXTENSION)
        droot = dtree.getroot()

        # print(exestrip+DWARF_EXTENSION)

        ddx.address = True
        ddx.TraverseDtree(droot, [None]) # sets ddx.dtree_hashmap

        if '.so' in exe:
            root = Element('DYNAMIC_LIBRARY')
        else:
            root = Element('EXECUTABLE')
        root.set('binary', exe)

        # iterate over the source files creating the binary
        for file in flist:
            relpath = file[len(origpath)+1:]
            curfstrip = relpath[relpath.rfind('/')+1:relpath.rfind('.')]
            combstrip = os.path.join(outfolder, relpath, curfstrip)

            # collect calls, signs and offset information
            # all of this information goes to same file: final.whatever
            for num, EXT in enumerate([CALL_EXTENSION, SIGN_EXTENSION, OFFSET_EXTENSION]):        
                if not headerWrite[num]:
                    headerWrite[num] = True
                    os.system('head -n 1 ' + combstrip + EXT + ' >> ' + CURFINALFILE + EXT)
                    # print ('hwritten')
                os.system('tail -n +2 ' + combstrip + EXT + ' >> ' + CURFINALFILE + EXT)

            # collect clangs
            stree = ET.parse(combstrip + COMB_EXTENSION)
            sroot = stree.getroot()
            ddx.UpdateCtree (sroot)
            root.append(sroot)

        # link the addresses into the executables and emit the address files
        print ('Combined static info for ' + exenamestrip)

        # xmlstr = minidom.parseString(ET.tostring(root)).toprettyxml(indent='   ')
        # with open(exestrip+COMB_EXTENSION, 'w') as f:
        #     f.write(xmlstr)
        stree.write(exestrip+COMB_EXTENSION, encoding='utf-8')
        print ('Written combined clang for ' + exenamestrip)
        
        # create the address file in the exe/so's folder
        # treat mainexe specially, as externs also need to be emitted
        ddx.generate_var(root, exestrip+ADDRESS_EXTENSION, numexe == 0)

        rootlist.append(root)

        if numexe == 0: # need to add addresses from readelf
            os.system('mv ' + exestrip+ADDRESS_EXTENSION + ' ' + exestrip+'.temp'+ADDRESS_EXTENSION)
            os.system('readelf -sW '+exe+' | grep "OBJECT">'+exestrip+SYMTAB_EXTENSION)
            os.system('awk -f merge ' + exestrip+SYMTAB_EXTENSION + ' FS="\t" ' + \
                        exestrip+'.temp'+ADDRESS_EXTENSION + ' > ' + exestrip+ADDRESS_EXTENSION)
        
        address_files.append(exestrip+ADDRESS_EXTENSION)
        os.system('cp ' + exestrip + ADDRESS_EXTENSION + ' ' + foutfolder+'/')

        print ('Generated addresses for ' + exenamestrip)
        
    patched_xml = ddx.patch_external_def_ids(rootlist)

    # finalxmlstr = minidom.parseString(ET.tostring(patched_xml)).toprettyxml(indent='   ')
    # with open(CURFINALFILE + STATIC_EXTENSION, 'w') as f:
    #     f.write(finalxmlstr)
    mytree = ET.ElementTree(patched_xml)
    mytree.write(CURFINALFILE+STATIC_EXTENSION, encoding='utf-8')

    uniquify(CURFINALFILE, STATIC_EXTENSION, CALL_EXTENSION,
        SIGN_EXTENSION, OFFSET_EXTENSION, address_files)

    print ('\nWritten interlinked combined clang for ' + executable)

        
def generate_static_info():
    print('Starting Static: '+ executable)

    # This function extract the dependencies of the binary under study, and
    # recursively finds out the list of source files responsible for this executable
    # and gets the executable's DWARF information and concats them
    
    # get list of all cpp's forming this executable
    ls = dict()

    def get_rec_deps(path):
        recdeps = []
        if path not in dependencies:
            return recdeps
        for x in dependencies[path]:
            if x[-2:] == '.o':
                recdeps.append(dependencies[x])
            elif x[-2:] == '.a':
                recdeps.extend(get_rec_deps(x))
            elif x.find('.so') != -1:
                add_loaded_binaries(x)
        return recdeps

    def add_loaded_binaries(path):
        ls[path] = get_rec_deps(path)

    add_loaded_binaries(executable)

    orderls = [(executable, ls[executable])]
    os.system('ldd '+executable+' > ldd.info')
    with open('ldd.info', 'r') as f:
        for line in f:
            r = line.strip().split()
            if (len(r) == 4): # location available
                libloc = os.path.realpath(r[2])
                if libloc in ls:
                    orderls.append((libloc, ls[libloc]))
    # os.system('rm ldd.info')
    if DEBUG:
        print (orderls)
    combine_all_clang(orderls)

def generate_dynamic_info(path, test, runidx, runNum):
    # Add dynamic_information to the combined static XML
    global project_name
    print('Starting Dynamic!')
    # print (test)
    if test is None:
        os.system(f'./pin.sh {executable} {foutfolder} {runidx} {runNum}')
    else:
        os.system(f'./pin.sh {executable} {foutfolder} {runidx} {runNum} "{test}"')
    print('Dynamic Done!')
    return 'dynamic.xml'

def generate_comments_info(project_name, project_path, vocab_file, problem_domain_file, output_file):
    # Return relative path (wrt to this file) to the comments' XML output
    print('Starting Comments!')

    # Need to use the exact source locations because comments' location gets mangled
    os.system('python3 '+ os.path.join(COMMENTS_FOLDER, "GenerateCommentsXMLForAFolder.py") + \
        " " + os.path.abspath(project_path) + " " \
        " " + os.path.abspath(os.path.join(OUTPUTS_FOLDER, project_name)) + " " + vocab_file + \
        " " + problem_domain_file + " " + project_name)

    os.system('python3 ' + os.path.join(COMMENTS_FOLDER, "MergeAllCommentsXML.py") + " " + \
        os.path.abspath(project_path) + " " + \
        os.path.abspath(os.path.join(OUTPUTS_FOLDER, project_name)) + "  " + output_file)
    print('Comments Done!')

def start_website():
    # Start the user inerface to query
    os.system('cp static.xml website/static.xml')
    os.system('cp dynamic.xml website/dynamic.xml')
    os.system('cp vcs.xml website/vcs.xml')    
    os.system('cp comments.xml website/comments.xml')
    os.system('cp dependencies.p website/dependencies.p')
    os.chdir('website')
    os.system('chmod +x setup.sh')
    os.system('./setup.sh')

def collect_results(project_name, executable):
    exec_name = executable.split('/')[-1]
    colpath = project_name + '/' + exec_name
    if not os.path.exists(colpath):
        os.mkdir(colpath)
    os.system('cp dependencies.p ' + colpath)
    os.system('cp static.xml ' + colpath)
    os.system('cp static.funcargs ' + colpath)
    os.system('cp ' + project_name + '/statinfo/*.offset ' + colpath)
    os.system('cp static.calls ' + colpath)  
    if CALLDYN:
        os.system('cp dynamic.xml ' + colpath)
        os.system('cp ' + exec_name + '.dump ' + colpath)
    if CALLCOMM:
        os.system('cp comments.xml ' + colpath)
    if CALLDYN and CALLCOMM:
        os.system ('> final_universal.xml')
        os.system ('cat static.xml dynamic.xml comments.xml > final_universal.xml')
        os.system('cp final_universal.xml ' + colpath) 
    print ('Information collected in: ', colpath)


jsonInfo = json.loads(open(sys.argv[1], "r").read())

runs = jsonInfo['runs']
for exe in runs:
    executable = os.path.abspath(exe)
    execstrip = executable[executable.rfind('/')+1:]
    origpath = executable[:executable.rfind('build/')-1]
    project_name = origpath[origpath.rfind('/')+1:]
    outfolder = os.path.abspath(os.path.join(OUTPUTS_FOLDER, project_name))
    foutfolder = os.path.join(outfolder,'exe_'+execstrip)
    os.system('mkdir -p ' + foutfolder)

    # Parse dependencies
    dependencies = pickle.load(open(os.path.join(outfolder, 'dependencies.p'), 'rb'))

    if CALLSTATIC:
        generate_static_info()

    # Generate dynamic data
    if CALLDYN:
        for idx, ti in enumerate(runs[exe]):
            if len(ti) > 0:
                test_input = os.path.abspath(ti)
                generate_dynamic_info(executable, test_input, idx, runs[exe][ti])
            else:
                generate_dynamic_info(executable, None, idx, runs[exe][ti])
            os.system("mv " + os.path.join(foutfolder, "final_dynamic.xml") + " " + \
                os.path.join(foutfolder, "final_dynamic_" + str(idx) + ".xml"))

if CALLCOMM:
    # comments_config
    cc = jsonInfo['comments']
    if 'project_path' not in cc:
        project_path = os.path.join(PROJECTS_FOLDER, cc['project_name'])
    else:
        project_path = cc['project_path']
    generate_comments_info(cc['project_name'], project_path, cc['vocab_loc'], \
    cc['problem_domain_loc'], os.path.join(outfolder, FINAL_FILE+COMMENTS_EXTENSION))

if CALLVCS:
    # vcs_config
    if jsonInfo['vcs']['fresh_fetch']:
        vcs.generate_vcs_info(jsonInfo['vcs'], os.path.join(outfolder, FINAL_FILE+VCS_EXTENSION))

# collect_results(project_name, executable)

# start_website()
