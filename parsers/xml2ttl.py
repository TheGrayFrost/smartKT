# Run this on the final all-combined XML
# Fixes multiple header file inclusion problem
# and converts to TTL

# Usage: python xml2ttl.py <fileName>
# Output: TTL file with same filename and extension .ttl

from xml.etree.ElementTree import Element, SubElement
from xml.etree import ElementTree as ET
from xml.dom import minidom

# combined_file = sys.argv[1]
combined_file = "inherit.temp.xml"
cctree = ET.parse(combined_file).getroot()

usr2id = {}

TTLstring = """
@prefix id:   <http://smartkt.org/id> .
@prefix attribute:   <http://smartkt.org/attribute> .
@prefix relation:   <http://smartkt.org/relation> .
@prefix property:   <http://smartkt.org/property> .
@prefix object: <http://smartkt.org/object> .
@prefix usr: <http://smartkt.org/usr> .

"""

def visitChild(xmlNode, xmlParent):
    global TTLstring
    if 'usr'in xmlNode.attrib:
        if xmlNode.attrib['usr'] in usr2id:
            return
    nodeid = str(xmlNode.attrib['id'])
    parentid = str(xmlParent.attrib['id'])
    base_str = "id:"+nodeid+" "
    TTLstring += base_str+ "relation:isA object:" + xmlNode.tag + " .\n"
    TTLstring += base_str+ "relation:ast_parent id:"+parentid + " .\n"
    TTLstring += "id:"+parentid+" relation:ast_child "+base_str+" .\n"

    for attr in xmlNode.attrib:
        if attr == "spelling":
            TTLstring += base_str+"attribute:spelling \""+ xmlNode.attrib['spelling'] +"\" .\n"
        if attr == "file":
            TTLstring += base_str+"attribute:file \"" + xmlNode.attrib['file'] + "\" .\n"
        if attr == "line":
            TTLstring += base_str+"attribute:line \"" + xmlNode.attrib['line'] + "\" .\n"
        if attr == "col":
            TTLstring += base_str+"attribute:col \"" + xmlNode.attrib['col'] + "\" .\n"
        if attr == "range.start":
            TTLstring += base_str+"attribute:range_start \"" + xmlNode.attrib['range.start'] + "\" .\n"
        if attr == "range.end":
            TTLstring += base_str+"attribute:range_end \"" + xmlNode.attrib['range.end'] + "\" .\n"
        if attr == "usr":
            TTLstring += base_str+"attribute:usr usr:\"" + xmlNode.attrib['usr'] + "\" .\n"
            usr2id[xmlNode.attrib['usr']] = nodeid
        if attr == "lex_parent_usr":
            TTLstring += base_str+"relation:lex_parent_usr usr:\"" + xmlNode.attrib['lex_parent_usr'] + "\" .\n"
            TTLstring += "usr:\""+ xmlNode.attrib['lex_parent_usr'] +"\" relation:lex_child_id " + base_str + ".\n"
        if attr == "sem_parent_usr":
            TTLstring += base_str+"relation:sem_parent_usr usr:\"" + xmlNode.attrib['sem_parent_usr'] + "\" .\n"
            TTLstring += "usr:\""+ xmlNode.attrib['sem_parent_usr'] +"\" relation:lex_child_id " + base_str + ".\n"
        if attr == "ref_usr":
            TTLstring += base_str+"relation:ref_usr usr:\"" + xmlNode.attrib['ref_usr'] + "\" .\n"
            TTLstring += "usr:\""+ xmlNode.attrib['ref_usr'] +"\" relation:referenced_id " + base_str + ".\n"
        if attr == "def_usr":
            TTLstring += base_str+"relation:def_usr usr:\"" + xmlNode.attrib['def_usr'] + "\" .\n"
            TTLstring += "usr:\""+ xmlNode.attrib['def_usr'] +"\" relation:defined_id " + base_str + ".\n"
        if attr == "type":
            TTLstring += base_str+"property:type \"" + xmlNode.attrib['type'] + "\" .\n"
        if attr == "isRef":
            TTLstring += base_str+"property:isRef \"" + xmlNode.attrib['isRef'] + "\" .\n"
        if attr == "isDef":
            TTLstring += base_str+"property:isDef \"" + xmlNode.attrib['isDef'] + "\" .\n"
        if attr == "isDecl":
            TTLstring += base_str+"property:isDecl \"" + xmlNode.attrib['isDecl'] + "\" .\n"
        if attr == "access_specifier":
            TTLstring += base_str+"property:access_specifier \"" + xmlNode.attrib['access_specifier'] + "\" .\n"
        if attr == "linkage_kind":
            TTLstring += base_str+"property:linkage_kind \"" + xmlNode.attrib['linkage_kind'] + "\" .\n"

    for child in xmlNode.getchildren():
        visitChild(child, xmlNode)

idx = 0
for tu in cctree.getchildren():
    tu.attrib['id'] = idx
    idx += 1
    for child in tu.getchildren():
        visitChild(child, tu)

with open(sys.argv[1][:-4] + ".ttl", "w") as f:
    f.write(TTLstring)
