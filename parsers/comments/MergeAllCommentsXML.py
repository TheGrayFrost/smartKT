import os
import sys
from os.path import join as PJOIN
import xml.etree.ElementTree as ET

DEBUG = False

def MergeAll(folder_name):
    global COMMENT_ID, ROOT
    for file in os.listdir(folder_name):
        if os.path.isdir(PJOIN(folder_name, file)):
            MergeAll(PJOIN(folder_name, file))
            continue
        
        if not file.endswith("_comments.xml"):
            continue

        if DEBUG:
            print("Merging... ",PJOIN(folder_name, file))
        
        tree = ET.parse(PJOIN(folder_name, file))
        root = tree.getroot()
    
        for comment in root.getchildren():
            file_path = comment.attrib["src_file_location"]
            if file_path[:2] == '..':
                file_path = file_path[3:]
            comment.set('src_file_location', file_path)
            comment.set('id', str(COMMENT_ID))
            COMMENT_ID += 1
            ROOT.append(comment)

if len(sys.argv) != 3:
    print("Give 2 arguments - ProjectPath, Output XML FILE")

COMMENT_ID = 1
ROOT = ET.Element('COMMENTS')
project_name = (sys.argv[1].split('/')[-1])
ROOT.set('project_name', project_name)
ROOT.set('project_path', sys.argv[1])
MergeAll(sys.argv[1])

xml_data = ET.tostring(ROOT)
with open(sys.argv[2],'wb') as f:
    f.write(xml_data)
