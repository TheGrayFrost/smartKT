# To use:
# python dwarfdump_parser.py <dwarfdump_output> <output_extension>

'''
There is no clear algorithm here. Just hacks. I wrote this parser as I saw fit.
Can be prone to errors while parsing outputs that I haven't encountered yet.
I will try my best to explain what I have done, but I am no good.
'''

import sys
import os
from xml.etree.ElementTree import Element, SubElement
from xml.etree import ElementTree as ET
from xml.dom import minidom

def count_spaces(line):
    count = 0
    for i in line:
        if i == ' ':
            count += 1
        else:
            return count

def get_clear_tag_name(tag_name):
    idx = -1
    for i, c in enumerate(tag_name):
        if c.islower():
            idx = i
            break
    s = tag_name[idx:]
    return s

def add_attrs(node, attrs):
    for attr in attrs:
        ls = attr.split()
        ls = [x for x in ls if x != '']
        attr_name = get_clear_tag_name(attr.split()[0])
        attr_val = ' '.join(ls[1:])
        if len(attr_val.strip()) > 0:
            if attr_val[0] == '"' or attr_val[0] == '<':
                attr_val = attr_val[1:-1]
            node.set(attr_name, attr_val)
        else:
            if attr_name.find('yes') != -1:
                node.set(attr_name[:attr_name.find('yes')], attr_name[attr_name.find('yes'):])
            else:
                node.set(attr_name, 'True')
    return node

def recfunc(parent, i, level):
    # Level helps to see if this is a new section or a continuation
    # If you see one output, you will see that there are '<' marks at the beginning
    # of what is supposed to be one node.
    # If new section, get the lines which correspond to the attributes of the new node
    # When done, there will be information about children.
    global data
    while(i < len(data)):
        l, d = data[i]
        if d[0] == '<' and int(d[1:3]) == level + 1:
            curr_level = int(d[1:3])
            tag_name = d[4:].split(' ')[-1]
            tag_name = get_clear_tag_name(tag_name)
            s = SubElement(parent, tag_name)
            s.set('id', d[4:].split()[0][1:-1])
            attrs = []
            i += 1
            if i < len(data):
                l, d = data[i]
                while get_clear_tag_name(d).split()[0] == 'ranges':
                    r = SubElement(s, 'ranges')
                    i += 1
                    l, d = data[i]
                    n = int(d.split()[1])
                    r.set('num_ranges', str(n))
                    r.set(d.split()[4], d.split()[5])
                    r.set(d.split()[8][:-1], d.split()[7][1:])
                    text = ''
                    for j in range(i+1, i+n+1):
                        text += data[j][1] + '\n'
                    r.text = text
                    i += n+1
                    if i < len(data):
                        l, d = data[i]
                    else:
                        return parent, i
            else:
                return parent, i
            while d[0] != '<' or (d[0] =='<' and d[1:3] == 'Un'):
                attrs.append(d)
                i += 1
                if i < len(data):
                    l, d = data[i]
                    while get_clear_tag_name(d).split()[0] == 'ranges':
                        r = SubElement(s, 'ranges')
                        i += 1
                        l, d = data[i]
                        n = int(d.split()[1])
                        r.set('num_ranges', str(n))
                        r.set(d.split()[4], d.split()[5])
                        r.set(d.split()[8][:-1], d.split()[7][1:])
                        text = ''
                        for j in range(i+1, i+n+1):
                            text += d[j] + '\n'
                        r.text = text
                        i += n+1
                        if i < len(data):
                            l, d = data[i]
                        else:
                            return parent, i
                else:
                    s = add_attrs(s, attrs)
                    return parent, i
            s = add_attrs(s, attrs)
        elif d[0] == '<' and int(d[1:3]) > curr_level:
            s, i = recfunc(s, i, curr_level)
        elif d[0] == '<' and int(d[1:3]) < curr_level:
            return parent, i
        else:
            return parent, i
    return parent, i


def fill_params(root):
    # For class based functions
    for c in root.findall('.//class_type'):
        for func in  c.findall('.//subprogram'):
            # find the matching specification
            for f in root.findall(".//*[@specification='"+func.attrib['id'] +"']"):
                for key in f.attrib:
                    func.set(key, f.attrib[key])
                for child in list(func):
                    func.remove(child)
                for child in list(f):
                    func.append(child)
                root.remove(f)
                break
    return root

def fill_abstract(root):
    for f in root.findall('.//*'):
        if 'abstract_origin' in f.attrib:
            # find the node with abstract_origin id
            for node in root.findall(".//*[@id='"+f.attrib['abstract_origin']+"']"):
                # copy the attributes except the abstract_origin attribute
                for key in f.attrib:
                    if key != 'abstract_origin':
                        node.set(key, f.attrib[key])
    for f in list(root.findall('.//*')):
        if 'abstract_origin' in f.attrib:
            try:
                root.remove(f)
            except:
                continue
    return root

def get_cu(root):
    global data
    s = SubElement(root, 'compile_unit')
    i = 1
    while i < len(data) and data[i].strip()[:6] == 'DW_AT_':
        p = data[i].split()
        s.set(p[0][6:], p[1])
        i += 1
    s.attrib['fname'] = os.path.abspath(os.path.join(s.attrib['comp_dir'], s.attrib['name']))
    return root, s
'''
STEP One: Open the file, read the contents, split on lines.
Observations:
    * sections are separated by a newline
    * Each section represents one tag (at least)
Steps:
1. Filter the section of concern
2. Create a root, and try to parse the output recursively
'''

root = Element('root')

filename = str(sys.argv[1])
with open(filename, 'r') as f:
    curdata = f.readlines()

data = None

oncomp = False
onloc = False
for idx, sentence in enumerate(curdata):
    if sentence.find('COMPILE_UNIT<') != -1:
        start_pos = idx
        oncomp = True
    elif oncomp and sentence == '\n':
        data = curdata[start_pos+1:idx]
        root, cu = get_cu(root)
        oncomp = False
    elif sentence == 'LOCAL_SYMBOLS:\n':
        start_pos = idx
        onloc = True
    elif onloc and sentence == '\n':
        data = curdata[start_pos+1:idx]
        data = [(count_spaces(x), x.strip()) for x in data]
        # Get the dwarfdump information in XML format
        cu, _ = recfunc(cu, 0, 0)
        # Add the abstract_origin type outputs. encountered during Constructors
        cu = fill_abstract(cu)
        # Add the offsets for function parameters.
        cu = fill_params(cu)
        onloc = False

xmlstr = minidom.parseString(ET.tostring(root)).toprettyxml(indent='   ')

outfilename = filename[:filename.rfind('.')] + sys.argv[2]
with open(outfilename, 'w') as f:
    f.write(xmlstr)
# print('File written at: ', filename)
