#!/usr/bin/env python3

import os
import sys

from xml.etree.ElementTree import Element, SubElement
from xml.etree import ElementTree as ET
from xml.dom import minidom
from collections import defaultdict

id_tags = {"id", "lex_parent_id", "sem_parent_id", "def_id", "ref_id", "ref_tmp"}

def uniquify(input_filename, output_filename) :
    xtree = ET.parse(input_filename)
    xroot = xtree.getroot()

    node_map = dict()
    id_map = dict()

    for node in xroot.iter() :
        if "id" in node.attrib :
            node_id = int(node.attrib["id"])
            node_data = tuple( sorted( { key: value
                    for key, value in node.attrib.items()
                    if key not in id_tags }.items() ) )

            if node_data not in node_map :
                node_map[ node_data ] = node_id
            id_map[ node_id ] = node_map[ node_data ]

    # print(node_map, id_map)

    def traverse(node, parent=None) :
        if parent is not None and "id" in node.attrib :
            node_id = int(node.attrib["id"])
            if id_map[ node_id ] != node_id :
                return True
            for id_tag in id_tags :
                if id_tag in node.attrib :
                    node_id_tag_val = int(node.attrib[id_tag])
                    if node_id_tag_val in id_map :
                        node.attrib[id_tag] = str(id_map[node_id_tag_val])

        cross_set = set()
        for child in node :
            if traverse(child, node) :
                cross_set.add(child)
        for child in cross_set :
            node.remove(child)
        return False

    traverse(xroot, None)

    output = ET.tostring(xroot)
    output = minidom.parseString(output).toprettyxml(indent='', newl='')
    with open(output_filename, "w") as fh :
        print(output, file=fh)

    
if __name__ == "__main__" :
    In = sys.argv[1]
    Out = sys.argv[2]
    uniquify(In, Out)
