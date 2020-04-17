#!/usr/bin/env python3
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


refmap = dict() # to link specification to the originating nodes

# takes a binary file's path, an xml root
# and adds the debug info in the binary to the xml root
def process_file(filename, xml_root):

	with open(filename, 'rb') as f:
		# read the binary
		elffile = ELFFile(f)

		if not elffile.has_dwarf_info():
			print('{} has no DWARF info'.format(filename), file=sys.stderr)
			return

		# extract dwarf info
		dwarfinfo = elffile.get_dwarf_info()

		# set global state info about elf
		set_global_machine_arch(elffile.get_machine_arch())

		# For optimized code, the machine code doesn't exactly correspond to the source lines
		# In such cases, compiler adds .debug_loc section in the ELF to aid with this source
		# location matching. We parse that section here. It would usually be emptyin absence of 
		# -O flags passed to the compiler
		location_lists = dwarfinfo.location_lists()
		loc_parser = LocationParser(location_lists)

		# Add path to binary
		file_xml_root = XMLSubElement(xml_root, 'file')
		file_xml_root.set('name', str(filename))

		# Each source file (.cpp/.c) with all it's included headers etc. after preprocessing is called
		# a translation unit (TU). The compiler compiles it into object code which is referred to as a
		# compilation unit (CU). So, a .so/.a library built of many .o's would contain many CU's

		# Each DWARF information line is called a Debugging Information Entry (DIE)
		# Each DIE has an offset which is the byte offset of that DIE from the debug section start

		# We are iterating over the dwarf info for all CU's
		for CU in dwarfinfo.iter_CUs():

			top_DIE = CU.get_top_DIE()

			# cu_xml_root is the xml root holding info for this CU
			cu_xml_root = XMLSubElement(file_xml_root, str(top_DIE.tag))

			for key, value in CU.header.items() :
				cu_xml_root.set(key, str(value))
			# path of the TU that generated this CU
			cu_xml_root.set('path', str(top_DIE.get_full_path()))
			cu_xml_root.set('offset', str(CU.cu_offset))

			# This function adds the file table for each CU to cu_xml_root. Note that a CU may be composed of 
			# multiple files as there are the included files as well in the TU.
			def add_source_file_info(xml_parent) :
				# Add source file name index from the debug_line section
				filepath = os.path.abspath(filename)
				line_prog = dwarfinfo.line_program_for_CU(CU)
				# The include directories are held in dirs
				# Note that the path 
				dirs = [ os.path.dirname(filepath) ] + \
						list(map(lambda x: x.decode('utf-8'),
						line_prog['include_directory']))

				file_table_node = XMLSubElement(xml_parent, str("sources"))
				for i, file_entry in enumerate(line_prog['file_entry'], 1) :
					idx = file_entry['dir_index']
					source_file = file_entry['name'].decode('utf-8')
					entry = os.path.join(dirs[idx], source_file)

					# adding file table entry to xml
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
							print("{} warning : {}:".format(sys.argv[0], filename),
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

					if 'DW_FORM_ref' in attr_values.form:
						xml_attr += CU.cu_offset
					if isinstance(xml_attr, bytes) :
						xml_node.set(attr_name, xml_attr.decode('utf-8'))
					else :
						xml_node.set(attr_name, str(xml_attr))

				# NOTE: There is the implicit belief that the specification comes after the
				# referred DIE. If that turns out not to be the case later, which is quite unlikely,
				# we will need to do this linking in two passes

				# add node to map
				if 'offset' in xml_node.attrib:
					refmap[xml_node.attrib['offset']] = xml_node

				# after node construction, if it contains specification, add info onto refed node
				if 'DW_AT_specification' in xml_node.attrib:
					refed_node = refmap[xml_node.attrib['DW_AT_specification']]
					for k, v in xml_node.attrib.items():
						if k not in refed_node.attrib and k != 'DW_AT_specification':
							refed_node.set(k, v)

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
