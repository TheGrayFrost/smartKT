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
            comment.set('comment_id', str(COMMENT_ID))
            COMMENT_ID += 1
            ROOT.append(comment)

if len(sys.argv) != 4:
    print("Give 2 arguments - ProjectPath OutputDirectory OutputXMLFileName")

COMMENT_ID = 1
ROOT = ET.Element('COMMENTS')
project_name = (sys.argv[1].split('/')[-1])
ROOT.set('project_name', project_name)
ROOT.set('project_path', sys.argv[1])
MergeAll(sys.argv[2])

xml_data = ET.tostring(ROOT)
with open(sys.argv[3],'w') as f:
    f.write(xml_data)