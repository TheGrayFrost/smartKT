#!/usr/bin/env python3

import os
import sys
import tempfile

from xml.etree.ElementTree import Element, SubElement
from xml.etree import ElementTree as ET
from xml.dom import minidom
from collections import defaultdict

# These are the only tags that are used to index, identify or
# or point to the nodes. (See parsers/ast2xml.cc, calls to makeUniqueID().)
id_tags = {
    "id", "lex_parent_id", "sem_parent_id", "def_id", "ref_id", "ref_tmp"}

# setting it here for running on server
# as /tmp on server is mount point for a different storage media
# leads to failure during cross-device link creation
tempfile.tempdir = os.getcwd()

def remap(file_name, field_ids, id_map, delim='\t') :
    """
    For a tab (or other) delimited file, change the old IDs to new IDs,
    using the translations in id_map.
    field_ids are the indices of columns that hold some identifier.
    id_map is the translation map.

    Note that if the some ID has no translation in the id_map,
    that ID is left unchanged.
    Also, in the process deletes any malformed data that doesn't have
    an identifier in some of the id field columns.
    """
    with open(file_name, "r") as input_file, \
        tempfile.NamedTemporaryFile(mode="w", delete=False) as tmpf :
        # open the input file and a temporary file

        header = input_file.readline().strip() # read file header
        print(header, file=tmpf)

        for line in input_file :
            data = line.strip().split(delim)
            printok = True # print only if all id fields are non empty
            for idx in field_ids :
                if data[idx] == '':
                    printok = False
                    break
                ref_id = int(data[idx])
                if ref_id in id_map : # can be translated to a new ID...
                    ref_id = id_map[ ref_id ] # ...so we must do it
                data[idx] = str( ref_id ) # change old ID to the new one.
            if printok:
                print(delim.join(data), file=tmpf)

    os.replace(tmpf.name, file_name) # replace original with the created temporary

def remap_tree(tree, id_map) :
    """
    Performs the same job as remap(), but for an XML element tree.
    Again, "dangling" (unseen) IDs in the tree are left unchanged.
    """
    for node in tree.iter() :
        for id_tag in id_tags :
            if id_tag in node.attrib :
                node_id_tag_val = int(node.attrib[id_tag])
                if node_id_tag_val in id_map : # If this ID can be translated...
                    node.attrib[id_tag] = str(id_map[node_id_tag_val]) # ... do it


def uniquify(CURFINALFILE, STATIC_EXTENSION, CALL_EXTENSION,
        SIGN_EXTENSION, OFFSET_EXTENSION, ADDRESS_FILES ) :
    """
    This function uniquifies nodes and updates the identifiers
    and the pointers in all static files using the same mapping.

    Does so by first creating an ID function that maps the set of
    old IDs to the set of new IDs. Multiple old IDs are mapped to a single
    new ID if and only if they have identical content.
    Two nodes are said to have identical content if they have exactly the
    same attribute - value pairs, except all of their "id_tags" defined above.
    """

    input_filename = CURFINALFILE + STATIC_EXTENSION

    xtree = ET.parse(input_filename)
    xroot = xtree.getroot()

    node_map = dict() # Maps the contents of a node to one of the IDs.
    id_map = dict() # Maps an old ID to a new ID, using node_map.

    def traverse(node, parent=None) :
        """
        Performs a post - order traversal of the syntax tree and
        populates the node_map and id_map tables.
        Removes a node from the tree if the entire subtree is full
        of duplicate nodes.
        A node is duplicate if there is another node with
        identical content that has been recorded in the node_map
        at some earlier point in the traversal, and all of its
        descendants are also duplicate.
        """

        cross_set = set() # Remember which children have to be removed.
        for child in node :
            if traverse(child, node) : # if some subtree is removed
                cross_set.add(child)

        for child in cross_set :
            node.remove(child)

        duplicate_node = False
        # set true if this node, and all of its descendants can be removed.

        if "id" in node.attrib and len(node) == 0 : # All subtrees have been removed.
            node_id = int(node.attrib["id"])

            kvpairs = { key: value
                    for key, value in node.attrib.items()
                    if key not in id_tags }
            kvpairs["tag"] = node.tag
            node_data = tuple( sorted( kvpairs.items() ) )
            # node_data is a hashable, sorted tuple of key-value pairs, which
            # forms the content of current node. This is used to determine
            # if some future node is duplicate.

            duplicate_node = node_data in node_map # The content is not new.

            if not duplicate_node : # The content is new, so we update our tables.
                node_map[ node_data ] = node_id

            id_map[ node_id ] = node_map[ node_data ]
            # Map this node id to some node ID having the same content, possibly self.
        # ...
        # else: there is some descendant with previously unseen data,
        # that is specific to this translation unit's version of the syntax node,
        # so we can't remove it from its parent.

        return duplicate_node # Return true, only if this node can be removed from its parent.

    traverse(xroot, None) # populate id_map

    # id_map now stores a map that can be used to translate old IDs to new IDs.
    # So we apply this map on the the id_tags of all the static files.
    remap(CURFINALFILE + CALL_EXTENSION, {3}, id_map)
    remap(CURFINALFILE + SIGN_EXTENSION, {1}, id_map)
    remap(CURFINALFILE + OFFSET_EXTENSION, {4, 7}, id_map)

    for address_file in ADDRESS_FILES :
        remap(address_file, {2, 5}, id_map)

    # Now we update the XML tree itself, to store the new IDs instead of the old ones.
    remap_tree(xroot, id_map)

    output = ET.tostring(xroot)
    output = minidom.parseString(output).toprettyxml(indent='', newl='')

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmpf :
        print(output, file=tmpf) # print output to temporary file
    os.replace(tmpf.name, input_filename) # replace original with the created temporary
