import sys
import argparse
import xml.dom.minidom
from xml.dom.minidom import parse
from rdflib import Graph, Literal, BNode, Namespace, RDF, URIRef
from rdflib.namespace import XSD
import pickle

DEBUG = False

g = Graph()

#Defining the prefixes
sequence = Namespace("http://smartKT/ns/sequence#")
prop = Namespace("http://smartKT/ns/properties#")
symbol = Namespace("http://smartKT/ns/symbol#")

g.bind("sequence",sequence)
g.bind("prop",prop)

count = 0

def get_id(nodeId):

    while nodeId and nodeId != mapping_extra_id[nodeId]:
        nodeId = mapping_extra_id[nodeId]

    return nodeId


def add_attributes(node,INP,RUNID):

    global count
    allAttributes = node.attributes.items()
    count += 1

    for each in allAttributes:
        subj = str(each[0])
        obj = str(each[1])

        if(subj == "THREADID"):
            g.add( (sequence[str(count)], prop['thread_id'], Literal(obj,datatype=XSD.integer)) )
        if(subj == "READCOUNT"):
            g.add( (sequence[str(count)], prop['read_count'], Literal(obj,datatype=XSD.integer)) )
        if(subj == "WRITECOUNT"):
            g.add( (sequence[str(count)], prop['write_count'], Literal(obj,datatype=XSD.integer)) )
        if(subj == "VARID"):
            nodeId = str(obj)
            nodeId = get_id(nodeId)
            if DEBUG:
                print(nodeId)
            g.add( (sequence[str(count)], prop['var_id'], symbol[nodeId]) )
        if(subj == "RETVAL"):
            g.add( (sequence[str(count)], prop['return_value'], Literal(obj)) )
        if(subj == "SYNCS"):
            g.add( (sequence[str(count)], prop['sync'], Literal(obj)) )
            if obj == "1":
                for child in node.childNodes:
                    if child.nodeType != child.TEXT_NODE:
                        posix_type = child.getAttribute("TYPE")
                        g.add( (sequence[str(count)], prop['posix_lock'], Literal(posix_type)) )
        if(subj == "VARNAME"):
            g.add( (sequence[str(count)], prop['var_name'], Literal(obj)) )
        if(subj == "CALLEENAME"):
            g.add( (sequence[str(count)], prop['callee_name'], Literal(obj)) )
        if(subj == "CALLERNAME"):
            g.add( (sequence[str(count)], prop['caller_name'], Literal(obj)) )
        if(subj == "VARCLASS"):
            g.add( (sequence[str(count)], prop['var_class'], Literal(obj)) )
        if(subj == "FUNCNAME"):
            g.add( (sequence[str(count)], prop['func_name'], Literal(obj)) )
        if(subj == "OFFSET"):
            g.add( (sequence[str(count)], prop['offset'], Literal(obj)) )

    if node.tagName == "NONLOCALREAD":
        g.add( (sequence[str(count)], prop['NONLOCALREAD'], Literal("True")) )

    if node.tagName == "NONLOCALWRITE":
        g.add( (sequence[str(count)], prop['NONLOCALWRITE'], Literal("True")) )

    g.add( (sequence[str(count)], prop['is_a'], Literal(node.tagName)) )
    g.add( (sequence[str(count)], prop['RUNID'], Literal(RUNID)) )
    g.add( (sequence[str(count)], prop['INP'], Literal(str(INP))) )


def iterate_section(node,INP,RUNID):

    add_attributes(node,INP,RUNID)

    for child in node.childNodes:
        if child.nodeType != child.TEXT_NODE:
            add_attributes(child,INP,RUNID)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Files needed to run the code.')

    # Inputs
    parser.add_argument(dest='XMLFile', action='store', help='Input the Dynamic XML file path')
    parser.add_argument(dest='PICKLEFile', action='store', help='Input the PICKLE file path')

    # Outputs
    parser.add_argument(dest='TTLFile', action='store', help='Input the file path to store the generated TTL')

    args = vars(parser.parse_args())
    XMLFile = args['XMLFile']
    TTLFile = args['TTLFile']
    PICKLEFile = args['PICKLEFile']

    mapping_extra_id = pickle.load( open(PICKLEFile, "rb" ) )

    if DEBUG:
        print(len(mapping_extra_id))

    DOMTree = xml.dom.minidom.parse(XMLFile)
    collection = DOMTree.documentElement

    allTags = collection.getElementsByTagName("DYNAMICTRACE")

    if DEBUG:
        print(allTags)
    RUNID = 0
    INPID = 0

    inp_files = list()

    for tag in allTags:
        RUNID = tag.getAttribute("RUNID")
        INP = tag.getAttribute("INP").split("/")[-1]

        if INP not in inp_files:
            inp_files.append(INP)

        INPID = inp_files.index(INP)

        for child in tag.childNodes:
            if child.nodeType != child.TEXT_NODE:
                iterate_section(child,INPID,RUNID)
    g.serialize(TTLFile,format='ttl')
