# Usage:
# python3 aggregrate.py <final_static.xml> <final_cfg.cfg> <output_cfg.dot> [<dynamic_dump.dump>] <output_pickle.p>

import sys, pickle, os, json
from itertools import groupby
from xml.etree.ElementTree import Element, SubElement
from xml.etree import ElementTree as ET
from xml.dom import minidom

import cxxfilt
from functools import cmp_to_key

filename = sys.argv[2]
key = "St5D7yHzyE5WRpHRGuGVB6r4t4HK47TRS69Gka7Pfc2d2wArVrmyPtUZbEUxVMrZ"
func2loc = {}
func2entry = {}
func2exit = {}
func2calls = {}
func2spell = {}
numBlocks = {}
block2coverage = {}
blockGraph = {}
block2range = {}
superCalls = {}
myCallGraph = {}
func2coverage = {}
functionMaps = {}
stree = None

with open(filename, "r") as f:
    data = f.readlines()

data = [x.strip() for x in data]
data = [list(group) for k, group in groupby(data, lambda x: x == key) if not k]
basicBlocks = data[::2]
callGraph = data[1::2]

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

def range2List(ls):
    temp = ls[1:-1].split(':')
    temp = [int(x) for x in temp]
    return temp

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

def getStartLoc(func):
    for caller in stree.findall('.//*[@linkage_name="'+func+'"]'):
        if 'isDef' in caller.attrib:
            return caller.attrib['range.start']

def getEndLoc(func):
    for caller in stree.findall('.//*[@linkage_name="'+func+'"]'):
        if 'isDef' in caller.attrib:
            return caller.attrib['range.end']

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

def locComapre(r1, r2):
    if not isinstance(r1, list):
        r1, r2 = range2List(r1), range2List(r2)
    if r1[0] == r2[0]:
        return r1[1] - r2[1]
    return r1[0] - r2[0]

def isContained(totRange, firstPoint, secondPoint=None):
    if locComapre(totRange[:2], firstPoint) <= 0 and locComapre(firstPoint, totRange[2:]) <= 0:
        return True
    elif secondPoint is not None and locComapre(totRange[:2], secondPoint) <= 0 and locComapre(secondPoint, totRange[2:]) <= 0:
        return True
    else:
        return False

def getAlternateMangledName(funcID):
    s = stree.find('.//*[@id="'+funcID+'"]')
    if s.attrib['linkage_name'] not in func2entry:
        return createNewFunction(s.attrib['linkage_name'])
    return s.attrib['linkage_name']

def createNewFunction(func, funcID=None):
    instanceNode = None
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
    if funcID is not None:
        return getAlternateMangledName(funcID)

def processBlockRange(block, ranges, visited):
    currRange = block2range[block]
    matchRanges = [x for x in ranges if isContained(currRange, range2List(x[1]), range2List(x[2]))]
    ranges = [x for x in ranges if x not in matchRanges]

    def match_cmp(a, b):
        return locComapre(a[2], b[2])
    matchRanges = sorted(matchRanges, key = cmp_to_key(match_cmp))

    func = block.split('#')[0]
    currBlock = block
    visited.add(currBlock)
    for match in matchRanges:
        newBlock = func+"#"+str(numBlocks[func])
        numBlocks[func] += 1
        block2coverage[newBlock] = False
        match1 = range2List(match[2])
        block2range[newBlock] = match1 + block2range[currBlock][2:]
        block2range[currBlock] = block2range[currBlock][:-2] + match1
        blockGraph[newBlock] = blockGraph[currBlock]
        if match[0] not in func2entry:
            createNewFunction(match[0])
        blockGraph[currBlock] = [func2entry[match[0]]]
        blockGraph[func2exit[match[0]]].append(newBlock)
        currBlock = newBlock
        visited.add(newBlock)
    return currBlock

def getPossibleBlocks(record):
    possibleBlocks = []
    reqLineNumber = int(record['INSLOC'].split(':')[1])
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

def isConstructor(funcID):
    for x in stree.findall('.//*[@id="'+funcID+'"]'):
        if x.tag == "CXXConstructor" or x.tag == "CXXDestructor":
            return True
    return False

def isSuperCall(record):
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

def isUnhandledConstructor(record):
    if isConstructor(record['CALLEENODEID']):
        reqLineNumber = record['INSLOC'].split(':')[1]
        func = stree.find('.//*[@id="'+record['CALLERNODEID']+'"]')
        for callee in func.findall('.//CallExpr[@def_id="'+record['CALLEENODEID']+'"]'):
            if range2List(callee.attrib['range.start'])[0] == reqLineNumber or \
            range2List(callee.attrib['range.end'])[0] == reqLineNumber:
                # It is not likely to be an implicitly called constructor since
                # it is in the same line as that of a constructor call to the same
                # class. Here we are again limited by PIN's column API
                return False
        return True
    return False

def specialContained(totRange, firstPoint, secondPoint=None):
    if locComapre(totRange[:2], firstPoint) <= 0 and locComapre(firstPoint, totRange[2:]) <= 0:
        return True
    elif secondPoint is not None and locComapre(totRange[:2], secondPoint) <= 0 and locComapre(secondPoint, totRange[2:]) <= 0:
        return True
    else:
        return False

def getCurrentBlockFromTrace(record, lastBlockVisited):
    func = stree.find('.//*[@id="'+record['CALLERNODEID']+'"]')
    funcName = func.attrib['linkage_name']
    possibleCalls, reqLineNumber = [], int(record['INSLOC'].split(':')[1])
    possibleBlocks, lastCol = [], None

    # Find possible function calls that might match our requirement
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

def processFunc(func):
    ranges = getCallInstanceRanges(func)
    if len(ranges) == 0:
        return
    myCallGraph[func] = [x[0] for x in ranges]
    func2coverage[func] = False

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

def processDump(ls):
    dict_merge = lambda a,b: a.update(b) or a
    ls = ls[1:]
    ls = [dict_merge({'RECTYPE': rec[0], 'INSLOC': rec[rec.index('INSLOC')+1]}, {rec[i]: rec[i+1] for i in range(1, len(rec)-1, 2)}) for rec in ls]
    lastBlockVisited = []
    callStack = []
    for idx, record in enumerate(ls):
        try:
            if record['RECTYPE'] == 'WRITE' or record['RECTYPE'] == 'READ':
                # Identify all possible basicBlocks and mark them true
                listOfBlocks = getPossibleBlocks(record)
                for i in listOfBlocks:
                    block2coverage[i] = True
                lastBlockVisited = listOfBlocks
            elif record['RECTYPE'] == 'CALL':
                func, callee = record['CALLERNAME'], record['CALLEENAME']
                callStack.append(record['CALLEENODEID'])
                # Handle Constructors/Destructors differently, as they don't show
                if func not in func2entry:
                    func = createNewFunction(func, record['CALLERNODEID'])
                if isSuperCall(record):
                    if func not in superCalls:
                        superCalls[func] = func2entry[func]
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
                # elif isUnhandledConstructor(record):
                #     currBlock, lastCol = getCurrentBlockFromTrace(record, lastBlockVisited, True)
                #     newBlock = func+"#"+str(numBlocks[func])
                #     numBlocks[func] += 1
                #     block2coverage[newBlock] = False
                #     block2range[newBlock] = [record['INSLOC'].split(':')[1]+1, 0]
                #     block2range[newBlock].append(block2range[currBlock][2:])
                #     block2range[currBlock] = block2range[currBlock][:2] + [record['INSLOC'].split(':')[1], lastCol]
                #     if callee not in func2entry:
                #         createNewFunction(callee)
                #     blockGraph[currBlock] = [func2entry[callee]]
                #     blockGraph[func2exit[callee]].append(newBlock)
                #     block2coverage[currBlock] = True
                #     block2coverage[func2entry[callee]] = True
                #     lastBlockVisited = [func2entry[callee]]
                else:
                    currBlock = getCurrentBlockFromTrace(record, lastBlockVisited)
                    if callee not in func2entry:
                        callee = createNewFunction(callee, record['CALLEENODEID'])

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
                func, funcID = record['FUNCNAME'], record['FUNCNODEID']
                func = getAlternateMangledName(funcID)
                callStack.pop()
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
                        print("ERROR")
                        # print(record, idx, possibleReturnPoints)
                    if len(possibleReturnPoints) == 1:
                        block2coverage[possibleReturnPoints[0]] = True
                        lastBlockVisited = possibleReturnPoints
                    # else, we are not sure what is the next basic block
                    # We can only hope, that the basic blocks get identified through
                    # subsequent instructions
                    lastBlockVisited = [func2exit[func]]
        except:
            # print(record)
            continue

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

    runFiles = sys.argv[4:-1]
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
    # json.dump(block2coverage, open("templates/static/images/block2coverage.json", 'w'), indent=4)
    # block2coverage = json.loads(open("templates/static/images/block2coverage.json", 'r').read())

    # Sample code: To extract the exact sentences in the source by using block2range
    funcList = list(func2entry.keys())
    block2labels = {k:"SampleCode" for k in blockGraph}
    pickle.dump((funcList, block2coverage, block2labels), open(sys.argv[-1], "wb"))
