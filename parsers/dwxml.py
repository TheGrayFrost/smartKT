#!/usr/bin/env python
import sys
import os

sys.path[0:0] = [".", ".."]

import pyelftools
from pyelftools.elftools.elf.elffile import ELFFile
from pyelftools.elftools.dwarf.descriptions import (
    describe_DWARF_expr, set_global_machine_arch)
from pyelftools.elftools.dwarf.locationlists import (
    LocationEntry, LocationExpr, LocationParser)

from xml.etree.ElementTree import (
    Element as XMLElement, SubElement as XMLSubElement)
from xml.etree import ElementTree as XMLElementTree
from xml.dom import minidom as XMLMiniDOM


def process_file(filename, xml_root):

    with open(filename, 'rb') as f:
        elffile = ELFFile(f)

        if not elffile.has_dwarf_info():
            print(f'{filename} has no DWARF info', file=sys.stderr)
            return

        dwarfinfo = elffile.get_dwarf_info()

        set_global_machine_arch(elffile.get_machine_arch())

        # Can be used to parse .debug_loc sections, which is usually empty
        # in absence of -O flags to the compiler
        location_lists = dwarfinfo.location_lists()
        loc_parser = LocationParser(location_lists)

        file_xml_root = XMLSubElement(xml_root, 'file')
        file_xml_root.set('name', str(filename))

        for CU in dwarfinfo.iter_CUs():

            top_DIE = CU.get_top_DIE()

            cu_xml_root = XMLSubElement(file_xml_root, str(top_DIE.tag))

            for key, value in CU.header.items() :
                cu_xml_root.set(key, str(value))
            cu_xml_root.set('path', str(top_DIE.get_full_path()))

            def add_source_file_info(xml_parent) :
                """ Add source file name index from the debug_line section.
                """
                filepath = os.path.abspath(filename)
                line_prog = dwarfinfo.line_program_for_CU(CU)
                dirs = [ os.path.dirname(filepath) ] + \
                        list(map(lambda x: x.decode('utf-8'),
                        line_prog['include_directory']))

                file_table_node = XMLSubElement(xml_parent, str("sources"))
                for i, file_entry in enumerate(line_prog['file_entry'], 1) :
                    idx = file_entry['dir_index']
                    source_file = file_entry['name'].decode('utf-8')
                    entry = os.path.join(dirs[idx], source_file)

                    xml_node = XMLSubElement(file_table_node, 'entry')
                    xml_node.set('id', str(i))
                    xml_node.set('file', entry)

            add_source_file_info(cu_xml_root)

            def add_die_info(DIE, xml_parent) :
                """ Recursively process all DIEs.
                """
                xml_node = XMLSubElement(xml_parent, DIE.tag)

                xml_node.set('offset', str(DIE.offset))

                for attr_name, attr_values in DIE.attributes.items() :
                    # FIXME: update pyelftools/elftools/dwarf/enums.py
                    if not isinstance(attr_name, str) :
                        if not args.quiet :
                            print(f"{sys.argv[0]} warning : {filename}:",
                                    " unknown attribute :", attr_values,
                                    file=sys.stderr)
                        continue

                    xml_attr = attr_values.value
                    if loc_parser.attribute_has_location(
                                attr_values, CU['version']) :
                        loc = loc_parser.parse_from_attribute(
                                    attr_values, CU['version'])
                        if isinstance(loc, LocationExpr) :
                            # location lists not yet supported
                            xml_attr = describe_DWARF_expr(
                                    loc.loc_expr, dwarfinfo.structs)

                    if isinstance(xml_attr, bytes) :
                        xml_node.set(attr_name, xml_attr.decode('utf-8'))
                    else :
                        xml_node.set(attr_name, str(xml_attr))

                for child_DIE in DIE.iter_children() :
                    add_die_info(child_DIE, xml_node)

            # Process DIEs recursively starting with top_DIE
            for child in top_DIE.iter_children() :
                add_die_info(child, cu_xml_root)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description="dump DWARF debug info in XML format.")
    parser.add_argument('-o', '--outfile', dest='output_file',
            default=None, help="output to file")
    parser.add_argument(dest='object_files', nargs='+',
            help="non empty list of object files")
    parser.add_argument('-q', '--quiet', action='store_true',
            help="suppress errors")

    try :
        args = parser.parse_args()
    except Exception as e :
        parser.print_help()
        exit(1)

    xml_root = XMLElement('root')

    for object_file in args.object_files :
        process_file(object_file, xml_root)

    output = XMLElementTree.tostring(xml_root)
    output = XMLMiniDOM.parseString(output).toprettyxml(indent='  ')

    if args.output_file :
        with open(args.output_file, 'w') as outfile :
            print(output, file=outfile)
    else :
        print(output)
