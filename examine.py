# Before you can use, specify the details in config.txt file
# To use:
# python examine.py <clean/retain> <project_name> <vocab_file> <problem_domain_file> <path_to_executable> {path_to_input_file}


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

DWARF_EXTENSION = '_dd.xml'
COMB_EXTENSION = '_comb.xml'
CALL_EXTENSION = '.calls'
SIGN_EXTENSION = '.funcargs'
OFFSET_EXTENSION = '.offset'
ADDRESS_EXTENSION = '.address'
TEMP_EXTENSION = '.temp.xml'
FINAL_FILE = 'final'
STATIC_EXTENSION = '_static.xml'
DYNAMIC_EXTENSION = '_dynamic.xml'

CALLDYN = False
CALLCOMM = False

executable = os.path.abspath(sys.argv[1])
test_input = None
n = 2
if CALLCOMM:
    n = 4
    vocab_file = sys.argv[2]
    problem_domain_file = sys.argv[3]
if len(sys.argv) > n:
    test_input = sys.argv[n]

execstrip = executable[executable.rfind('/')+1:]
origpath = executable[:executable.rfind('build/')-1]
project_name = origpath[origpath.rfind('/')+1:]
outfolder = os.path.abspath('outputs/'+project_name)
foutfolder = os.path.join(outfolder,'exe_'+execstrip)
os.system('mkdir ' + foutfolder)

(dependencies, sourcefile, objectfile) = pickle.load(open(os.path.join(outfolder, 'dependencies.p'), 'rb'))

# get list of all cpp's forming this executable
def get_rec_deps(path):
    recdeps = []
    for x in dependencies[path]:
        if x[-2:] == '.o':
            recdeps.append(sourcefile[x])
        else:
            recdeps.extend(get_rec_deps(x))
    return recdeps

# [TODO]
# Instead of combining by exclusive parsing, we can simply echo out to file
# See combine_all_domain.sh, for example
def combine_all_clang(depmap):
    CURFINALFILE = os.path.join(foutfolder, FINAL_FILE)

    for EXT in [CALL_EXTENSION, SIGN_EXTENSION, OFFSET_EXTENSION, STATIC_EXTENSION]:
        os.system('> ' + os.path.join(foutfolder, CURFINALFILE+EXT))

    headerWrite = [False, False, False]
    for num, (exe, flist) in enumerate(depmap.iteritems()):
        exenamestrip = exe[exe.rfind('/')+1:]
        exeoutfolder = os.path.join(foutfolder, exenamestrip)
        exestrip = os.path.join(exeoutfolder, exenamestrip)
        os.system('mkdir ' + exeoutfolder)
        print ('\nGenerating info for ' + exenamestrip)

        root = Element('EXEC_STATIC')
        root.set('executable', exe)
        for file in flist:
            relpath = file[len(origpath)+1:]
            curfstrip = relpath[relpath.rfind('/')+1:relpath.rfind('.')]
            combstrip = os.path.join(outfolder, relpath, curfstrip)

            # collect calls, signs and offset information
            for num, EXT in enumerate([CALL_EXTENSION, SIGN_EXTENSION, OFFSET_EXTENSION]):
                if not headerWrite[num]:
                    headerWrite[num] = True
                    os.system('head -n 1 ' + combstrip + EXT + ' >> ' + CURFINALFILE + EXT)
                    # print ('hwritten')
                os.system('tail -n +2 ' + combstrip + EXT + ' >> ' + CURFINALFILE + EXT)

            # collect clangs
            stree = ET.parse(combstrip + COMB_EXTENSION)
            sroot = stree.getroot()
            root.append(sroot)

        print ('Combined static info for ' + exenamestrip)

        xmlstr = minidom.parseString(ET.tostring(root)).toprettyxml(indent='   ')
        with open(exestrip+TEMP_EXTENSION, 'w') as f:
            f.write(xmlstr)
        print ('Written temp clang for ' + exenamestrip)

        # generate dwarfdump and its xml for the so or the main executable
        os.system('dwarfdump -i ' + exe + ' > ' + exestrip+'.dd')
        os.system('python parsers/dwarfdump_parser.py ' +exestrip+'.dd ' + DWARF_EXTENSION)
        print ('Created dwarfdump for ' + exenamestrip)

        # link the addresses into the executables and emit the address files
        COMBINE_OUTEXT = ' '.join([DWARF_EXTENSION, TEMP_EXTENSION, COMB_EXTENSION, ADDRESS_EXTENSION])
        os.system('python parsers/combine.py ' + exestrip + ' ADDRESS ' + COMBINE_OUTEXT)
        os.system('cp ' + exestrip + ADDRESS_EXTENSION + ' ' + foutfolder+'/')
        print ('Generated addresses for ' + exenamestrip)
        # combine address patched xmls into one final static xml
        os.system('cat ' + exestrip + COMB_EXTENSION + ' >> ' + CURFINALFILE + STATIC_EXTENSION)

def generate_static_info():
    print('Starting Static!')

    # This function extract the dependencies of the binary under study, and
    # recursively finds out the list of source files responsible for this executable
    # and gets the executable's DWARF information and concats them
    ls = defaultdict(list)
    for x in dependencies[executable]:
        if x[-2:] == '.o':
            ls[executable].append(sourcefile[x])
        elif x[-2:] == '.a':
            ls[executable].extend(get_rec_deps(x)) # .a's are also statically linked
        elif x.find('.so') != -1:
            ls[x] = get_rec_deps(x) # .so dynamic links treated separately

    combine_all_clang(ls)

def generate_dynamic_info(path, test=None):
    # Add dynamic_information to the combined static XML
    global project_name
    print('Starting Dynamic!')
    if test is None:
        os.system('./pin.sh {} {}'.format(executable, foutfolder))
    else:
        os.system('./pin.sh {} {} {}'.format(executable, foutfolder, test))
    print('Dynamic Done!')
    return 'dynamic.xml'

def generate_comments_info(project_name, vocab_file, problem_domain_file):
    # Return relative path (wrt to this file) to the comments' XML output
    print('Starting Comments!')
    if not os.path.exists('comments/temp'):
        os.mkdir('comments/temp')
    if not os.path.exists('comments/temp/'+project_name):
        os.mkdir('comments/temp/'+project_name)
    os.system('python2 comments/GenerateCommentsXMLForAFolder.py /workspace/projects/ ' + project_name +
        ' /workspace/' + project_name + ' ' + vocab_file + ' ' + problem_domain_file+ ' ' +
        '/workspace/comments/temp/'+project_name)
    os.system('python2 comments/MergeAllCommentsXML.py ' + '/workspace/comments/temp/' + project_name +
        ' /workspace/' + project_name + ' ' + '/workspace/projects/'+ project_name +
        ' /workspace/comments.xml')
    print('Comments Done!')
    return 'comments.xml'

def generate_vcs_info(project_name):
    print('Starting VCS!')
    os.system('python vcs.py')
    print('VCS Done!')
    return 'vcs.xml'

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

generate_static_info()

if CALLDYN:
    dynamic_file = generate_dynamic_info(executable, test_input)
if CALLCOMM:
    comments_file = generate_comments_info(project_name, vocab_file, problem_domain_file)
# if isClean:
#     vcs_file = generate_vcs_info(project_name)
# collect_results(project_name, executable)

# start_website()
