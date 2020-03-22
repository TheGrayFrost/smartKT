#!/usr/bin/env python3
import sys
import os

sys.path[0:0] = [".", ".."]
import pyelftools
from pyelftools.elftools.elf.elffile import ELFFile

from collections import defaultdict

from pyelftools.elftools import __version__
from pyelftools.elftools.common.exceptions import ELFError
from pyelftools.elftools.elf.elffile import ELFFile
from pyelftools.elftools.elf.dynamic import DynamicSection, DynamicSegment

from xml.etree.ElementTree import Element, SubElement
from xml.etree import ElementTree as ET
from xml.dom import minidom

# The order of translation units should be the same as the one given to the linker.
# Since libraries might contain multiple compilation units
# whose symbol resolution order is given here :
# https://eli.thegreenplace.net/2013/07/09/library-order-in-static-linking 
# the order of "picking up" compilation units from them should determine the order
# of patching symbol reference information in respective translation units
# and hence the order in which we pass arguments to this function.
def patch_external_def_ids(translation_units, output_filename) :
    patched_xml = ET.Element("elf")

    exported_symbols = dict() # Set of all external USRs.
    requested_symbols = defaultdict(list)

    for tu_id, filename in enumerate(translation_units) :

        with open(filename, 'r') as xml_file :
            tu_tree = ET.parse(xml_file)

            root_node = tu_tree.getroot()
            root_node.set("id", str(tu_id))
            patched_xml.append(root_node)

            for node in tu_tree.iter() :
                if all(attr in node.attrib for attr in ("usr", "linkage_kind")) :
                    if node.attrib["linkage_kind"] != "external" :
                        continue

                    if ("isDef" in node.attrib and node.attrib["isDef"] == "True") :
                        exported_symbols[ node.attrib["usr"] ] = (tu_id, node)

                        if node.attrib["usr"] in requested_symbols :
                            for _, request in requested_symbols[ node.attrib["usr"] ] :
                                request.attrib["def_id"] = str(tu_id) + ":" + node.attrib["id"]
                            requested_symbols.pop( node.attrib["usr"] )

                    else : # Not a definition.
                        if node.attrib["usr"] in exported_symbols :
                            def_tu, def_node = exported_symbols[ node.attrib["usr"] ]
                            node.attrib["def_id"] = str(def_tu) + ":" + def_node.attrib["id"]
                        else :
                            requested_symbols[ node.attrib["usr"] ].append( (tu_id, node) )



    output = ET.tostring(patched_xml)
    output = minidom.parseString(output).toprettyxml(indent='  ')
    with open(output_filename, 'w') as output_file :
        print(output, file=output_file)


if __name__ == "__main__" :
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("static_xmls", nargs='+',type=str, help="static files")
    parser.add_argument("output", type=str, help="output_file")

    try :
        args = parser.parse_args()
    except Exception as e :
        parser.print_help()
        exit(1)

    patch_external_def_ids(args.static_xmls, args.output)
