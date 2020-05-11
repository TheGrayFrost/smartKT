#!/usr/bin/env python3
import sys
import os

from xml.etree.ElementTree import Element, SubElement
from xml.etree import ElementTree as ET
from xml.dom import minidom

# Tags for function declarations.
FunctionTags = {'CXXConstructor', 'CXXDestructor', 'CXXMethod', 'FunctionDecl'}

def emit_funcargs(input_filename, output_filename) :
    """
    Generates the .funcargs file.
    This just prints data already being extracted in static XML in a different format.
    """
    header = '# FILENAME\tFUNCNODEID\tFUNCNAME\tNARGS\tARGTYPE*\tRETTYPE'
    with open(input_filename, 'r') as xml_file, open(output_filename, 'w') as output_file :
        print(header, file=output_file)
        tu_tree = ET.parse(xml_file)
        for node in tu_tree.iter():
            if node.tag in FunctionTags:
                args = node.attrib['funcargs']
                if args != '':
                    args = args.split(',')
                # added check because template definitions have empty linkage name
                # and also are useless for us (?)
                if node.attrib['linkage_name'] != '':
                    print(node.attrib['file'], node.attrib['id'],
                        node.attrib['linkage_name'], len(args), '\t'.join(args),
                        node.attrib['return_type'], sep='\t', file=output_file)


if __name__ == '__main__' :
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('static_xml', type=str, help='static files')
    parser.add_argument('output', type=str, help='output file')

    try:
        args = parser.parse_args()
    except Exception as e :
        parser.print_help()
        exit(1)

    emit_funcargs(args.static_xml, args.output)
