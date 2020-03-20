# Run this on the final all-combined XML
# Fixes multiple header file inclusion problem
# and converts to TTL

# Usage: python3 xml2ttl.py <fileName>
# Output: TTL file with same filename and extension .ttl

from xml.etree.ElementTree import Element, SubElement
from xml.etree import ElementTree as ET
from xml.dom import minidom


idx = 0
usr2id = {}

TTLstring = '''
@prefix id:   <http://smartkt.org/id> .
@prefix attribute:   <http://smartkt.org/attribute> .
@prefix relation:   <http://smartkt.org/relation> .
@prefix property:   <http://smartkt.org/property> .
@prefix object: <http://smartkt.org/object> .
@prefix usr: <http://smartkt.org/usr> .
@prefix component: <http://smartkt.org/component> .
@prefix slib: <http://smartkt.org/component> .
@prefix dlib: <http://smartkt.org/component> .
@prefix obj: <http://smartkt.org/component> .
@prefix exe: <http://smartkt.org/component> .
'''

tag2prefix = {
    'STATIC_LIBRARY': 'slib',
    'DYNMAIC_LIBRARY': 'dlib',
    'OBJECT': 'obj',
    'EXEC_STATIC': 'exe'
}

tag2attrib = {
    'STATIC_LIBRARY': 'archive_name',
    'DYNMAIC_LIBRARY': 'shared_object_name',
    'OBJECT': 'object_file',
    'EXEC_STATIC': 'executable'
}

tag2comp = {
    'STATIC_LIBRARY': 'staticLibrary',
    'DYNMAIC_LIBRARY': 'dynamicLibrary',
    'OBJECT': 'object',
    'EXEC_STATIC': 'executable'
}

# basic attributes
tracked_attrs = {'spelling', 'file', 'line', 'col', 'range.start', 'range.end', 'usr'}
# usr-linking attributes
usr_linked_attrs = {'lex_parent_usr', 'sem_parent_usr', 'ref_usr', 'def_usr'}
usr_reverse = {'lex_parent_usr': 'lex_child_id', 'sem_parent_usr': 'sem_child_id',
                    'ref_usr': 'referenced_id', 'def_usr': 'defined_id'}
# properties
tracked_props = {'type', 'isRef', 'isDef', 'isDecl', 'access_specifier', 'linkage_kind'}


def visitChild(xmlNode, xmlParent):
    global TTLstring
    if 'usr'in xmlNode.attrib:
        # node already present.. no need to print again
        # resolves duplicate node generation when header file included in multiple files
        if xmlNode.attrib['usr'] in usr2id:
            return
    nodeid = str(xmlNode.attrib['id'])
    parentid = str(xmlParent.attrib['id'])
    base_str = 'id:'+nodeid+' '
    TTLstring += base_str+ 'relation:isA object:' + xmlNode.tag + ' .\n'
    TTLstring += base_str+ 'relation:ast_parent id:'+parentid + ' .\n'
    TTLstring += 'id:'+parentid+' relation:ast_child '+base_str+' .\n'

    for attr in xmlNode.attrib:
        if attr == 'usr':
            usr2id[xmlNode.attrib['usr']] = nodeid
        if attr in tracked_attrs:
            TTLstring += base_str+'attribute:'+attr+' \''+xmlNode.attrib[attr]+'\' .\n'
        elif attr in usr_linked_attrs:
            TTLstring += base_str+'relation:'+attr+' usr:\''+xmlNode.attrib[attr] + '\' .\n'
            TTLstring += 'usr:\''+xmlNode.attrib[attr]+'\' relation:'+usr_reverse[attr]+' '+base_str+'.\n'
        elif attr in tracked_props:
            TTLstring += base_str+'property:'+attr+' \''+xmlNode.attrib[attr]+'\' .\n'

    for child in xmlNode.getchildren():
        visitChild(child, xmlNode)

def visitComponent(xmlNode, parent):
    global tag2prefix
    # isA relation
    TTLstring += tag2prefix[xmlNode.tag] + ':\''+xmlNode.attrib[tag2attrib[xmlNode.tag]] + \
            '\' relation:isA component:'+ tag2comp[xmlNode.tag] +' .\n'
    if parent is not None:
        # partOf and composedOf relations
        TTLstring += tag2prefix[xmlNode.tag] + ':\''+xmlNode.attrib[tag2attrib[xmlNode.tag]] + \
                '\' relation:partOf ' + tag2prefix[xmlParent.tag]+':\'' + \
                xmlParent.attrib[tag2attrib[xmlParent.tag]] + '\' .\n'
        TTLstring += tag2prefix[xmlParent.tag]+':\'' + xmlParent.attrib[tag2attrib[xmlParent.tag]] + \
                '\' relation:composedOf '+ tag2prefix[xmlNode.tag] +':\'' + \
                 xmlNode.attrib[tag2attrib[xmlNode.tag]] + '\' .\n'

    if xmlNode.tag == 'OBJECT':
        TTLstring += 'obj:\'' + xmlNode.attrib['shared_object_name'] + 'relation:source \'' + \
                xmlNode.attrib['source_file'] +'\' .\n'
        for tu in xmlNode.getchildren():
            tu.attrib['id'] = idx
            idx += 1
            visitChild(child, tu)
    else:
        for child in xmlNode.getchildren():
            visitComponent(child, xmlNode)

combined_file = sys.argv[1]
ccroot = ET.parse(combined_file).getroot()
visitComponent(ccroot, None)

with open(sys.argv[1][:-4] + '.ttl', 'w') as f:
    f.write(TTLstring)
