# python mapping_extra_id.py ../../xml_csv_files/libpng_xml/final_static.xml ../../Data\ files/mapping_libpng_static.p

import sys
import re
import pickle
import argparse
import xml.dom.minidom
from xml.dom.minidom import parse
from rdflib import Graph, Literal, BNode, Namespace, RDF, URIRef
from rdflib.namespace import XSD
from collections import defaultdict


DEBUG = False

def get_id(node):

    isDECL = False
    isDEF = False
    nodeRefId = None
    nodeDefId = None

    storageClass = node.getAttribute("storage_class")

    if node.hasAttribute("id"):
        nodeId = str(node.getAttribute("id"))
    if node.hasAttribute("ref_id"):
        nodeRefId = str(node.getAttribute("ref_id"))
    if node.hasAttribute("def_id"):
        nodeDefId = str(node.getAttribute("def_id"))

    if node.hasAttribute("isDecl"):
        isDECL = True
    if node.hasAttribute("isDef"):
        isDEF = True

    if (isDECL and isDEF) or (isDECL and storageClass == "extern"):
        return nodeId

    if nodeRefId:
        return nodeRefId

    return nodeDefId


def add_all_triples(node,parent_node):

    nodeId = get_id(node)

    allAttributes = node.attributes.items()
    name = ''
    isDECL = False
    isDEF = False

    for attribute in allAttributes:
        subj = str(attribute[0])
        obj = str(attribute[1])

        if subj == "isDecl":
            isDECL = obj

        if subj == "isDef":
            isDEF = obj

        if subj == "id":
            temp_id = obj

    mapping_extra_id[temp_id] = nodeId


def iterate_node(node):

    ParentId = get_id(node)

    for child in node.childNodes:
        if child.nodeType != child.TEXT_NODE:
            if child.hasAttribute("spelling"):   #we add triples for only the ones that have spelling attribute
                add_all_triples(child,node)
            iterate_node(child)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='File needed to run the code.')
    parser.add_argument(dest='XMLFile', action='store', help='Input the Static XML file path')
    parser.add_argument(dest='pickle_file', action='store', help='Input the pickle file path')

    args = vars(parser.parse_args())
    XMLfile = args['XMLFile']
    pickle_file = args['pickle_file']

    mapping_extra_id = defaultdict(str)

    DOMTree = xml.dom.minidom.parse(XMLfile)
    collection = DOMTree.documentElement

    files = collection.getElementsByTagName("TranslationUnit")

    for file in files:
        iterate_node(file)

    if DEBUG:
        for key,value in mapping_extra_id.items():
            print(key,value)

    pickle.dump( mapping_extra_id, open( pickle_file, "wb"))
