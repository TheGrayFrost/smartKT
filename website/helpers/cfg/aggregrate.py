# Usage:
# python3 aggregrate.py <final_static.xml> <final_cfg.cfg> <output_cfg.dot> [<dynamic_dump.dump>]

import sys, pickle, os, json, random
from itertools import groupby
from xml.etree.ElementTree import Element, SubElement
from xml.etree import ElementTree as ET
from xml.dom import minidom

import cxxfilt
from functools import cmp_to_key

filename = sys.argv[2]

# This is the same key that was used to split different sections when we ran CFG tool
key = "St5D7yHzyE5WRpHRGuGVB6r4t4HK47TRS69Gka7Pfc2d2wArVrmyPtUZbEUxVMrZ"

# This is a list of dictionaries we maintain to compute the control flow graph
# Func : Function, loc: location, des: destructor

# Stores mapping between functions, and their location files and spelling respectively
func2loc = {}
func2spell = {}

# Stores the mapping of functions and their respective entry and exit basic blocks
# and whether the functions was visited
func2entry = {}
func2exit = {}
func2coverage = {} # redundant and deprecated

# mapping between functions and the number of basic blocks they contain
numBlocks = {}

# represents information from accumulated call graphs of all AST files
func2calls = {}

# mapping between basic blocks and their range, and if they were executed or not (actually during run time)
block2range = {}
block2coverage = {}

# Most important mapping, is a representation of the control flow graph
blockGraph = {}

# Is a way to handle constructor calls of parent classes. This information is only present
# in the dynamic trace
superCalls = {}

# represents the call graph information. For the time being, we are not using this
# as call graph can be better extracted from dynamic trace and from CFG (see cfg_dev.html for explanations).
# However, dynamic trace does miss some call graph information (things which might have been called and havenot)
myCallGraph = {}

# This is specifically for destructors as they are implicitly declared, and are not
# there on final_static.xml
desFunc2ID = {}
desID2Func = {}

# This is the XML for final_static
stree = None

# the following lines just reads final.cfg and converts it into a form that is
# easier to process further
with open(filename, "r") as f:
    data = f.readlines()

data = [x.strip() for x in data]
data = [list(group) for k, group in groupby(data, lambda x: x == key) if not k]
basicBlocks = data[::2]
callGraph = data[1::2]

# After this point, you should start looking from main function for better understanding

######################
#  HELPER FUNCTIONS  #
######################


# This function converts a list into DOT format and PNG image
def to_dot (li, fn):
    with open(fn + '.dot', 'w') as fp:
        fp.write('digraph G{\n')
        for el in list(set(li)):
            if type(el) in [list, tuple]:
                fp.write('"{}"->"{}"[label="{}"]\n'.format(el[0], el[1], el[2]))
            else:
                fp.write('"{}"\n'.format(el))
        fp.write('}\n')
    os.system("sfdp -Tpng -Goverlap=prism {}.dot -o {}.png".format(fn, fn))

# Converts a range in string format to list of integers of either
# [line, Col] or [startLine, startCol, endLine, endCol]
def range2List(ls):
    temp = ls[1:-1].split(':')
    temp = [int(x) for x in temp]
    return temp

# Given a function, find all instances of call expressions inside it
# and return the locations of the call expressions
def getCallInstanceRanges(func):
    ranges = []
    for caller in stree.findall('.//*[@linkage_name="'+func+'"]'):
        if 'isDef' in caller.attrib:
            for instance in caller.findall(".//CallExpr"):
                if 'ref_id' in instance.attrib:
                    ranges.append((stree.find('.//*[@id="'+instance.attrib['ref_id']+'"]')
                    .attrib['linkage_name'],
                    instance.attrib['range.start'],
                    instance.attrib['range.end']))
                else:
                    ranges.append((stree.find('.//*[@id="'+instance.attrib['def_id']+'"]')
                    .attrib['linkage_name'],
                    instance.attrib['range.start'],
                    instance.attrib['range.end']))
    return ranges

# Get starting location of functions
def getStartLoc(func):
    for caller in stree.findall('.//*[@linkage_name="'+func+'"]'):
        if 'isDef' in caller.attrib:
            return caller.attrib['range.start']

# Get ending location of functions
def getEndLoc(func):
    for caller in stree.findall('.//*[@linkage_name="'+func+'"]'):
        if 'isDef' in caller.attrib:
            return caller.attrib['range.end']

# Process each Basic Block. This doesn't do much except update the dictionaries
# mentioned above using the information extracted from cfg tool. Conversion to a
# more useful form
def processBB(bb):
    if len(bb) == 0:
        return
    func, loc = bb[0].split()
    func2loc[func] = loc
    n = int(bb[1])
    numBlocks[func] = n
    for i in range(2,2+n):
        id, ext, pred, succ = bb[i].split()
        currBlock = func+"#"+id
        block2coverage[currBlock] = False
        blockGraph[currBlock] = [func+"#"+str(x) for x in eval(succ)]
        if ext == "ENTRY":
            func2entry[func] = currBlock
            loc = getStartLoc(func)
            block2range[currBlock] = range2List(loc) + range2List(loc)
        elif ext == "EXIT":
            func2exit[func] = currBlock
            loc = getEndLoc(func)
            block2range[currBlock] = range2List(loc) + range2List(loc)
        else:
            block2range[currBlock] = eval(ext)
        if len(block2range[currBlock]) == 0:
            block2range[currBlock] = block2range[func+"#"+str(int(id)-1)]
    return processBB(bb[2+n:])

# Process each Call Graph. This doesn't do much except update the dictionaries
# mentioned above using the information extracted from cfg tool. Conversion to a
# more useful form
def processCGN(cgn):
    n = int(cgn[0])
    for i in range(1, 1+n):
        func, calls = cgn[i].split()
        func = func[:-1]
        for x in stree.findall('.//*[@linkage_name="'+func+'"]'):
            func2spell[func] = x.attrib['spelling']
        if calls[-2] == ',':
            calls = calls[1:-2].split(',')
        else:
            calls = []
        if func not in func2calls:
            func2calls[func] = set()
        func2calls[func].update(calls)

# Comparator for getting earlier locations between two locations
def locComapre(r1, r2):
    if not isinstance(r1, list):
        r1, r2 = range2List(r1), range2List(r2)
    if r1[0] == r2[0]:
        return r1[1] - r2[1]
    return r1[0] - r2[0]

# Checks if a given range contains the firstPoint, or if both firstPoint and
# secondPoint are given, then are these ranges overlapping
def isContained(totRange, firstPoint, secondPoint=None):
    if locComapre(totRange[:2], firstPoint) <= 0 and locComapre(firstPoint, totRange[2:]) <= 0:
        return True
    elif secondPoint is not None and locComapre(totRange[:2], secondPoint) <= 0 and locComapre(secondPoint, totRange[2:]) <= 0:
        return True
    else:
        return False

# This is due to multiple possible mangled names of constructors. We use this to
# get the one that was mentioned in the final_static.xml
def getAlternateMangledName(funcID):
    # Identify if it is destructor function, which doesn't have a body
    if funcID in desID2Func:
        return desID2Func[funcID]

    # Else, find the matching function by ID and return its name. If the entry
    # has not been reflected in the dictionaries, update accordingly by calling
    # createNewFunction
    s = stree.find('.//*[@id="'+funcID+'"]')
    if s.attrib['linkage_name'] not in func2entry:
        return createNewFunction(s.attrib['linkage_name'])
    return s.attrib['linkage_name']

# This helps us to create a basic block group
def createNewFunction(func, funcID=None):
    instanceNode = None
    # Find if the function exists by the same name in static XML, and create an entry for it
    for caller in stree.findall('.//*[@linkage_name="'+func+'"]'):
        if 'isDef' in caller.attrib:
            func2spell[func] = caller.attrib['spelling']
            func2loc[func] = caller.attrib['file']
            numBlocks[func] = 1
            currBlock = func+"#0"
            func2entry[func], func2exit[func] = currBlock, currBlock
            block2coverage[currBlock] = False
            blockGraph[currBlock] = []
            block2range[currBlock] = range2List(caller.attrib['range.start']) + range2List(caller.attrib['range.end'])
            return func
    # if not, find if it exists in static XML by some other name
    if funcID is not None:
        return getAlternateMangledName(funcID)

# given a implicitly declared destructor, find the class it represents
# and return its ID. (Algo inside)
def getDestructorClass(func):
    # demangle the function
    s = cxxfilt.demangle(func)
    # Split the function on scope resolution operator
    s = s.split('::')
    destNS = stree
    # Iteratively go one step down in possible nested Namespaces
    for i in range(len(s)-2):
        destNS = destNS.find('.//Namespace[@spelling="'+s[i]+'"]')
    # In the final Namespace, search for the class
    destClass = destNS.find('.//ClassDecl[@spelling="'+s[-2]+'"]')
    if destClass is not None:
        return destClass
    # Or it might be from a Structure
    destClass = destNS.find('.//StructDecl[@spelling="'+s[-2]+'"]')
    return destClass

# Does same job as createNewFunction, with slight modifications for
# implicitly declared functions
def insertDestructor(func):
    if func in func2entry:
        return
    func2spell[func] = cxxfilt.demangle(func)
    destructorClass = getDestructorClass(func)
    func2loc[func] = destructorClass.attrib['file']
    numBlocks[func] = 1
    currBlock = func+"#0"
    func2entry[func], func2exit[func] = currBlock, currBlock
    block2coverage[currBlock] = True
    blockGraph[currBlock] = []
    block2range[currBlock] = range2List(destructorClass.attrib['range.start']) + range2List(destructorClass.attrib['range.start'])
    desFunc2ID[func] = str(random.randint(1000000000000000, 9999999999999999))
    desID2Func[desFunc2ID[func]] = func

# Given a block of a function and a list of instances (lcoations) of call expressions inside
# the function, we need to split the blocks, add nodes and connect them. (Algo inside)
def processBlockRange(block, ranges, visited):
    # Get those call expressions which fall under the range of the current block
    currRange = block2range[block]
    matchRanges = [x for x in ranges if isContained(currRange, range2List(x[1]), range2List(x[2]))]
    ranges = [x for x in ranges if x not in matchRanges]

    # Sort the ranges (instances of call expressions), in a way that represents
    # the spirit of control flow. For example, consider A(b(), c()), details in thesis
    def match_cmp(a, b):
        return locComapre(a[2], b[2])
    matchRanges = sorted(matchRanges, key = cmp_to_key(match_cmp))

    # Find the function the block belongs to
    func = block.split('#')[0]
    currBlock = block
    visited.add(currBlock)
    # For each call expression
    for match in matchRanges:
        ################## SIMILAR STRATEGY IS FOLLOWED IN ALL CREATE NEW NODES/SPLITTING #############
        # create a newBlock
        newBlock = func+"#"+str(numBlocks[func])
        numBlocks[func] += 1

        # mark it unvisited
        block2coverage[newBlock] = False

        # update the ranges of current block and new block
        match1 = range2List(match[2])
        block2range[newBlock] = match1 + block2range[currBlock][2:]
        block2range[currBlock] = block2range[currBlock][:-2] + match1

        # transfer connections of current block to the new block
        blockGraph[newBlock] = blockGraph[currBlock]

        # if callee was not there in dictionaries, update
        if match[0] not in func2entry:
            createNewFunction(match[0])

        # point current block to entry point of calling function
        blockGraph[currBlock] = [func2entry[match[0]]]

        # point exit block of callee to the new block
        blockGraph[func2exit[match[0]]].append(newBlock)

        # set current block = new block
        currBlock = newBlock
        visited.add(newBlock)
    return currBlock

# This function is called for RW record
# It returns the list of blocks the read-write instruction might be present in.
# Please note, due to lack of column information from PIN, we cannot get the exact
# block and hence we have to return the list of all, and mark all of them visited
def getPossibleBlocks(record):
    possibleBlocks = []
    reqLineNumber = int(record['INSLOC'].split(':')[1])
    if 'FUNCNODEID' not in record:
        return func2entry['FUNCNAME']
    for func in stree.findall('.//*[@id="'+record['FUNCNODEID']+'"]'):
        # Get list of all variables with same line number
        possibleVars, funcName = [], func.attrib['linkage_name']
        for var in func.findall('.//*[@spelling="'+record['VARNAME']+'"]'):
            if range2List(var.attrib['range.start'])[0] == reqLineNumber:
                possibleVars.append(range2List(var.attrib['range.start']))
        # Find the basicBlocks that cover any of these variable
        for i in range(numBlocks[funcName]):
            currBlock = funcName + "#" + str(i)
            if len([1 for x in possibleVars if isContained(block2range[currBlock], x)]) > 0:
                possibleBlocks.append(currBlock)
    return list(set(possibleBlocks))


# Returns if a function denoted by its ID is a constructor or not (includes destructor
# to simplify implementations)
def isConstructor(funcID):
    for x in stree.findall('.//*[@id="'+funcID+'"]'):
        if x.tag == "CXXConstructor" or x.tag == "CXXDestructor":
            return True
    return False

# Returns if a function denoted by its ID is a destructor or not
# Algo, check if ~ symbol is there in the demangled name
def isDestructor(func):
    return cxxfilt.demangle(func).split('::')[-1][0] == '~'

# Identify if the call type is a constructor/destructor calling its baseclass's
# constructor/destructor because such relations are not there in final_static
def isSuperCall(record):
    if 'CALLEENODEID' not in record or 'CALLERNODEID' not in record:
        if 'CALLERNODEID' in record and stree.find('.//*[@id="'+record['CALLERNODEID']+'"]').tag != "CXXDestructor":
            return False
        elif 'CALLEENODEID' not in record and stree.find('.//*[@id="'+record['CALLEENODEID']+'"]').tag != "CXXDestructor":
            return False
        else:
            return True
    if isConstructor(record['CALLERNODEID']) and isConstructor(record['CALLEENODEID']):
        derivedClass = stree.find('.//CXXConstructor[@id="'+record['CALLERNODEID']+'"]...')
        if derivedClass.tag == 'TemplateStubs':
            derivedClass = stree.find('.//CXXConstructor[@id="'+record['CALLERNODEID']+'"]')
            classID = derivedClass.attrib['lex_parent_id']
            derivedClass = stree.find('.//ClassDecl[@id="'+classID+'"]')
            if derivedClass is None:
                derivedClass = stree.find('.//StructDecl[@id="'+classID+'"]')
        baseclass = stree.find('.//CXXConstructor[@id="'+record['CALLEENODEID']+'"]...')
        if baseclass.tag == 'TemplateStubs':
            baseclass = stree.find('.//CXXConstructor[@id="'+record['CALLEENODEID']+'"]')
            classID = baseclass.attrib['lex_parent_id']
            baseclass = stree.find('.//ClassDecl[@id="'+classID+'"]')
            if baseclass is None:
                baseclass = stree.find('.//StructDecl[@id="'+classID+'"]')

        for parentClass in derivedClass.findall("./CXXBaseClassSpecifier"):
            if parentClass.attrib['def_id'] == baseclass.attrib['id']:
                return True
    return False

# A destructor can be called explicitly, in which case it would have already been
# handled. Implicit destructor calls show up on the dynamic trace but not on static
# This function identifies if the destructor was not handled (from basic blocks point of view)
def isUnhandledDestructor(record):
    if isDestructor(record['CALLEENAME']):
        reqLineNumber = record['INSLOC'].split(':')[1]
        if 'CALLERNODEID' not in record:
            return False
        func = stree.find('.//*[@id="'+record['CALLERNODEID']+'"]')
        justName = cxxfilt.demangle(record['CALLEENAME']).split('::')[-1]
        for callee in func.findall('.//CallExpr[@spelling="'+justName+'"]'):
            if range2List(callee.attrib['range.start'])[0] == reqLineNumber or \
            range2List(callee.attrib['range.end'])[0] == reqLineNumber:
                # It is not likely to be an implicitly called destructor since
                # it is in the same line as that of a constructor call to the same
                # class. Here we are again limited by PIN's column API
                return False
        return True
    return False

# Sometimes we have to create one-block function where we combine the entry and
# exit into one, especially for artificial functions. While in hindsight,
# this isn't a good thing to do, the efforts to redo this with always creating
# at least 2 basic blocks is a much bigger task than just dealing with it on the go
# This function precisely does that. It splits a single block function into entry
# and exit blocks
def splitSingleBlockFunc(func):
    currBlock = func2entry[func]
    newBlock = func+"#"+str(numBlocks[func])
    numBlocks[func] += 1
    func2exit[func] = newBlock
    blockGraph[newBlock] = blockGraph[currBlock]
    blockGraph[currBlock] = [newBlock]
    block2coverage[newBlock] = False

# This function is just for implementation purposes
def specialContained(totRange, firstPoint, secondPoint=None):
    if locComapre(totRange[:2], firstPoint) <= 0 and locComapre(firstPoint, totRange[2:]) <= 0:
        return True
    elif secondPoint is not None and locComapre(totRange[:2], secondPoint) <= 0 and locComapre(secondPoint, totRange[2:]) <= 0:
        return True
    else:
        return False

# Given a call expression, this function returns the block from which the call
# was made. (Algo inside)
def getCurrentBlockFromTrace(record, lastBlockVisited):
    if 'CALLERNODEID' not in record:
        return func2entry[record['CALLEENAME']]
    func = stree.find('.//*[@id="'+record['CALLERNODEID']+'"]')
    funcName = func.attrib['linkage_name']
    possibleCalls, reqLineNumber = [], int(record['INSLOC'].split(':')[1])
    possibleBlocks, lastCol = [], None

    # Find possible function calls that might match our requirement
    if 'CALLEENODEID' not in record:
        justName = cxxfilt.demangle(record['CALLEENAME']).split('::')[-1]
        for callee in func.findall('.//CallExpr[@spelling="'+justName+'"]'):
            if range2List(callee.attrib['range.start'])[0] == reqLineNumber or\
            range2List(callee.attrib['range.end'])[0] == reqLineNumber:
                possibleCalls.append(range2List(callee.attrib['range.end']))
    else:
        for callee in func.findall('.//CallExpr[@def_id="'+record['CALLEENODEID']+'"]'):
            if range2List(callee.attrib['range.start'])[0] == reqLineNumber or\
            range2List(callee.attrib['range.end'])[0] == reqLineNumber:
                possibleCalls.append(range2List(callee.attrib['range.end']))

    # Find the basicBlocks that cover any of these functions
    for i in range(numBlocks[funcName]):
        currBlock = funcName + "#" + str(i)
        tmp = [pos for pos in possibleCalls if isContained(block2range[currBlock], pos)]
        if len(tmp) > 0:
            possibleBlocks.append(currBlock)

    if len(possibleBlocks) == 0:
        return func2entry[funcName]

    if len(possibleBlocks) >= 1:
        return possibleBlocks[0]

    # Different ways of filtering has to be applied here
    tmp = lastBlockVisited[:]
    while len(tmp) == 1:
        filtered = [currBlock for currBlock in possibleBlocks if currBlock in tmp]
        if len(firstFilter) == 1:
            if lastCol == True:
                ls = [pos for pos in possibleCalls if isContained(block2range[tmp[0]], pos)]
                ls = sorted(ls, key = cmp_to_key(locComapre))
                return filtered[0], ls[0]
            else:
                return filtered[0]
        tmp = blockGraph[tmp]

    return possibleBlocks[0]

# It takes a function, and traverses its basic blocks in a BFS manner
# and then prcesses these basic blocks additionally, using helper functions above
def processFunc(func):
    # Get List of call expressions in the function
    ranges = getCallInstanceRanges(func)

    # If no call expression is there, the basic block is correct (possible destructors will be handled later,
    # when encountered during runtime)
    if len(ranges) == 0:
        return

    myCallGraph[func] = [x[0] for x in ranges]
    func2coverage[func] = False

    # BFS traversal of basic blocks
    bfs = [func2entry[func]]
    visited = set()
    while(len(bfs) > 0):
        node = bfs[0]
        bfs = bfs[1:]
        visited.add(node)
        finalNode = processBlockRange(node, ranges, visited)
        for i in blockGraph[finalNode]:
            if i not in visited and i.split('#')[0] == func:
                bfs.append(i)

# This integrates the basic block with dynamic runtime trace, updates the basic
# block graph, marks blocks visited and creates the control flow graph. There can
# be many dumps, this function runs over one of such dump.
def processDump(ls):
    # Process the dump into more useful format
    dict_merge = lambda a,b: a.update(b) or a
    ls = ls[1:]
    ls = [dict_merge({'RECTYPE': rec[0], 'INSLOC': rec[rec.index('INSLOC')+1]}, {rec[i]: rec[i+1] for i in range(1, len(rec)-1, 2)}) for rec in ls]

    lastBlockVisited = [] # maintain last visited block, to help in ambiguous situations
    callStack = [] # return doesn't inform about which function it lands on after returning

    # There are 3 types of instructions: READ/WRITE, CALL, RETURNself.
    # Strong recommendation: detailed algo in thesis and their reasoning
    for idx, record in enumerate(ls):
        if record['RECTYPE'] == 'WRITE' or record['RECTYPE'] == 'READ':
            # Identify all possible basicBlocks and mark them true
            listOfBlocks = getPossibleBlocks(record)
            for i in listOfBlocks:
                block2coverage[i] = True
            lastBlockVisited = listOfBlocks
        elif record['RECTYPE'] == 'CALL':
            func, callee = record['CALLERNAME'], record['CALLEENAME']

            # If either caller or callee is an implicit destructor, add the nodes
            # PS: implicit destructors do not have nodeID
            if 'CALLERNODEID' not in record:
                insertDestructor(record['CALLERNAME'])
            if 'CALLEENODEID' not in record:
                insertDestructor(record['CALLEENAME'])

            # If callee is an implicit destructor, add corresponding nodeID
            if 'CALLEENODEID' not in record:
                callStack.append(desFunc2ID[record['CALLEENAME']])
            else:
                callStack.append(record['CALLEENODEID'])
            if func not in func2entry:
                func = createNewFunction(func, record['CALLERNODEID'])

            if numBlocks[func] == 1:
                splitSingleBlockFunc(func)

            # In case a derivedClass calls a baseclass's constructor/destructor
            if isSuperCall(record):
                # The idea is similar to adding nodes by splitting basic blocks,
                # except for 2 main differences:
                # 1. here no splitting of basic block is required, just reconfigure edges between basic blocks
                # 2. we need to keep track of the last end points after a parentClass's constructor has been called
                #    as the next baseclass constructor call will start from there, but the next baseclass constructor
                #    will be seen (if it exists) in some other instructions
                if func not in superCalls:
                    # we are adding first baseclass constructor, so we add from entry point of func
                    superCalls[func] = func2entry[func]

                # create a new block which will be the landing site of the return from
                # baseclass's constructor and update its properties similar to addition of a new block
                newBlock = func+"#"+str(numBlocks[func])
                numBlocks[func] += 1
                block2range[newBlock] = [0,0,0,0]
                blockGraph[newBlock] = blockGraph[superCalls[func]]

                if callee not in func2entry:
                    callee = createNewFunction(callee, record['CALLEENODEID'])
                blockGraph[superCalls[func]] = [func2entry[callee]]
                blockGraph[func2exit[callee]].append(newBlock)
                superCalls[func] = newBlock
                block2coverage[func2entry[func]] = True
                block2coverage[func2entry[callee]] = True
                lastBlockVisited = [func2entry[callee]]
            else:
                # Handle Constructors/Destructors differently, as they don't show in
                # final_static XML
                currBlock = getCurrentBlockFromTrace(record, lastBlockVisited)
                if callee not in func2entry:
                    callee = createNewFunction(callee, record['CALLEENODEID'])

                # possibly handle unhandled Destructors call grap h
                if isUnhandledDestructor(record):
                    # similar to splitting a block and adding a function
                    # described in processBlockRange
                    lastCol = 10000 # Some arbitrary large number (because of PIN's lack of column information)
                    newBlock = func+"#"+str(numBlocks[func])
                    numBlocks[func] += 1
                    block2coverage[newBlock] = False
                    block2range[newBlock] = [int(record['INSLOC'].split(':')[1])+1, 0]
                    block2range[newBlock].extend(block2range[currBlock][2:])
                    block2range[currBlock] = block2range[currBlock][:2] + [int(record['INSLOC'].split(':')[1]), lastCol]

                    if callee not in func2entry: # Seems redundant? Remove later
                        createNewFunction(callee)

                    blockGraph[currBlock] = [func2entry[callee]]
                    blockGraph[func2exit[callee]].append(newBlock)
                    block2coverage[currBlock] = True
                    block2coverage[func2entry[callee]] = True
                    lastBlockVisited = [func2entry[callee]]

                # Probable runtime polymorphism
                if func2entry[callee] not in blockGraph[currBlock]:
                    blockGraph[currBlock].append(func2entry[callee])
                    if len(blockGraph[currBlock]) > 0:
                        # Runtime Polymorphism
                        blockGraph[func2exit[callee]].append(func2exit[blockGraph[currBlock][0].split('#')[0]])
                    else:
                        if func2entry[func] == func2exit[func]:
                            # Super called
                            blockGraph[func2exit[callee]].append(func2exit[func])
                        else:
                            print("case not handled! Error")
                # Normal cases
                block2coverage[currBlock] = True
                block2coverage[func2entry[callee]] = True
                lastBlockVisited = [func2entry[callee]]
        elif record['RECTYPE'] == 'RETURN':
            # This return instructions are primarily used to verify the graph
            func = record['FUNCNAME']

            # Handle cases of destructors separately
            if 'FUNCNODEID' not in record:
                funcID = desFunc2ID[func]
            else:
                funcID = record['FUNCNODEID']

            func = getAlternateMangledName(funcID)
            try:
                callStack.pop()
            except:
                print("End of execution!") # Becase of last return call from main

            if len(callStack) == 0:
                callee = "main"
            else:
                callee = getAlternateMangledName(callStack[-1])

            # handle super calls
            block2coverage[func2exit[func]] = True
            if len(blockGraph[func2exit[func]]) == 1:
                block2coverage[blockGraph[func2exit[func]][0]] = True
                lastBlockVisited = blockGraph[func2exit[func]]
            else:
                possibleReturnPoints = [x for x in blockGraph[func2exit[func]] if x.split('#')[0]==callee]
                if len(possibleReturnPoints) == 0:
                    # We did not get even a single matching returnee! Debug if this shows
                    if idx == len(ls) - 1:
                        continue
                    else:
                        print("ERROR1")
                        print(record, idx, blockGraph[func2exit[func]], callee, func)
                if len(possibleReturnPoints) == 1:
                    # Best case scenario, we know exactly the block
                    block2coverage[possibleReturnPoints[0]] = True
                    lastBlockVisited = possibleReturnPoints
                # else, we are not sure what is the next basic block
                # (think about multiple calls to a function inside one function)
                # We can only hope, that the basic blocks get identified through
                # subsequent instructions
                lastBlockVisited = [func2exit[func]]

if __name__ == "__main__":
    stree = ET.parse(sys.argv[1]).getroot()

    # Create the Static Call Graph
    for cgn in callGraph:
        processCGN(cgn)

    for i in func2calls:
        func2calls[i] = list(func2calls[i])

    # Create the Basic Block Graph
    for bb in basicBlocks:
        processBB(bb)

    # Process Basic Block information for nonAritificalFunctions, i.e. functions
    # that have body
    nonAritificalFuncs = list(func2loc.keys())
    for func in nonAritificalFuncs:
        processFunc(func)

    # Add a false starting point to account for constructor calls in Global scope
    exec_start = 'EXEC_START'
    func2loc[exec_start] = func2loc['main']
    func2spell[exec_start] = exec_start
    numBlocks[exec_start] = 1
    currBlock = exec_start+"#0"
    func2entry[exec_start], func2exit[exec_start] = currBlock, currBlock
    block2coverage[currBlock] = True
    blockGraph[currBlock] = [func2entry['main']]
    block2range[currBlock] = [0,0,0,0]

    # Process each dynamic runtime trace
    runFiles = sys.argv[4:]
    for file in runFiles:
        data = open(file, 'r').readlines()
        data = [x.strip().split() for x in data]
        processDump(data)

    # Store BlockGraph
    ls = []
    for block in blockGraph:
        for caller in blockGraph[block]:
            ls.append((block, caller, ""))
    to_dot(ls, sys.argv[3])

    # Sample code: To extract the exact sentences in the source by using block2range
    funcList = list(func2entry.keys())
    block2labels = {k:"SampleCode" for k in blockGraph}
    pickle.dump((funcList, block2coverage, block2labels), open(sys.argv[3]+".p", "wb"))
