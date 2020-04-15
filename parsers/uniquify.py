#!/usr/bin/env python3

import os
import sys
import tempfile

from xml.etree.ElementTree import Element, SubElement
from xml.etree import ElementTree as ET
from xml.dom import minidom
from collections import defaultdict

id_tags = {
    "id", "lex_parent_id", "sem_parent_id", "def_id", "ref_id", "ref_tmp"}

def remap(file_name, field_ids, id_map, delim='\t') :
    with open(file_name, "r") as input_file, \
        tempfile.NamedTemporaryFile(mode="w", delete=False) as tmpf :

        header = input_file.readline().strip()
        print(header, file=tmpf)

        for line in input_file :
            data = line.strip().split(delim)
            for idx in field_ids :
                ref_id = int(data[idx])
                if ref_id in id_map :
                    ref_id = id_map[ ref_id ]
                data[idx] = str( ref_id )
            print(delim.join(data), file=tmpf)

    os.replace(tmpf.name, file_name)

def remap_tree(tree, id_map) :
    for node in tree.iter() :
        for id_tag in id_tags :
            if id_tag in node.attrib :
                node_id_tag_val = int(node.attrib[id_tag])
                if node_id_tag_val in id_map :
                    node.attrib[id_tag] = str(id_map[node_id_tag_val])


def uniquify(CURFINALFILE, STATIC_EXTENSION, CALL_EXTENSION,
        SIGN_EXTENSION, OFFSET_EXTENSION, ADDRESS_FILES ) :

    input_filename = CURFINALFILE + STATIC_EXTENSION

    xtree = ET.parse(input_filename)
    xroot = xtree.getroot()

    node_map = dict()
    id_map = dict()

    def traverse(node, parent=None) :

        cross_set = set()
        for child in node :
            if traverse(child, node) :
                cross_set.add(child)

        for child in cross_set :
            node.remove(child)

        duplicate_node = False

        if "id" in node.attrib and len(node) == 0 :
            node_id = int(node.attrib["id"])

            kvpairs = { key: value
                    for key, value in node.attrib.items()
                    if key not in id_tags }
            kvpairs["tag"] = node.tag
            node_data = tuple( sorted( kvpairs.items() ) )

            duplicate_node = node_data in node_map
            if not duplicate_node :
                node_map[ node_data ] = node_id
            id_map[ node_id ] = node_map[ node_data ]

        return duplicate_node

    traverse(xroot, None)

    remap(CURFINALFILE + CALL_EXTENSION, {3}, id_map)
    remap(CURFINALFILE + SIGN_EXTENSION, {1}, id_map)
    remap(CURFINALFILE + OFFSET_EXTENSION, {4, 7}, id_map)

    for address_file in ADDRESS_FILES :
        remap(address_file, {2, 5}, id_map)

    remap_tree(xroot, id_map)

    output = ET.tostring(xroot)
    output = minidom.parseString(output).toprettyxml(indent='', newl='')

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmpf :
        print(output, file=tmpf)
    os.replace(tmpf.name, input_filename)
