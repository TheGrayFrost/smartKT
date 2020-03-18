import sys, os
import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np
import xml.dom.minidom as minidom


def getKnowledgeBase(knowledge_base_path):
    csv_file = pd.read_csv(knowledge_base_path)
    csv_np = np.array(csv_file)
    knowledge_base = []
    for comment in csv_np:
        if "Copyright (c)" in comment[2]:
            continue
        else:
            knowledge_base.append([comment[2], comment[4], comment[7], comment[8], comment[15], comment[5], comment[6]])
    return knowledge_base

def createXML(project_name, project_path, file_location, outputprefix):
    root = ET.Element('COMMENTS')
    root.set('project_name', project_name)
    root.set('project_path', project_path)
    knowledge_base = getKnowledgeBase(outputprefix + "_knowledgeBase_commentsXML.csv")
    for comment in knowledge_base:
        comment_node = ET.SubElement(root, 'COMMENT')
        comment_node.set('src_file_location', file_location)

        comment_node.set('comment_text', comment[0])
        scope = comment[1].split(":")
        assert len(scope) == 2, "Scope does not contain exactly 2 integers!"
        comment_node.set('comment_scope_start', scope[0].strip())
        comment_node.set('comment_scope_end', scope[1].strip())
        if comment[2] != comment[2]:
            continue
        identifier_symbols = comment[2].split(" |||")
        identifier_symbols = [x.strip() for x in identifier_symbols]
        identifier_types = comment[3].split(" |||")
        identifier_ids = comment[4].split(" |||")
        identifier_ids = [x.strip() for x in identifier_ids]
        assert len(identifier_symbols) == len(identifier_types), ("Length of identifier_symbols and identifier_types DONOT match!", len(identifier_symbols), len(identifier_types))
        symbols_node = ET.SubElement(comment_node, 'SYMBOLS')

        for i in range(len(identifier_symbols)):
            identifier_type = identifier_types[i].split(":")
            identifier_type = [x.strip() for x in identifier_type]
            identifier_node = ET.SubElement(symbols_node, identifier_type[0])
            identifier_node.set('type', identifier_type[1])
            identifier_node.set('spelling', identifier_symbols[i])
            identifier_node.set('id', identifier_ids[i])

        if comment[5] != comment[5]:
            program_domains = []
        else:
            program_domains = comment[5].split("]  [")
        program_domains_node = ET.SubElement(comment_node, 'PROGRAM_DOMAINS')
        for program_domain in program_domains:
            if program_domain[0] == '[':
                program_domain = program_domain[1:]
            if program_domain[-1] == ']':
                program_domain = program_domain[:-1]
            word_and_type = program_domain.split(',')
            assert len(word_and_type) == 2, ("Length of Word And Type not equal to 2, it is:", len(word_and_type))
            if word_and_type[0][0]=="\'":
                word_and_type[0] = word_and_type[0][1:]
            if word_and_type[0][-1]=="\'":
                word_and_type[0] = word_and_type[0][:-1]
            if word_and_type[1][0]=="\'":
                word_and_type[1] = word_and_type[1][1:]
            if word_and_type[1][-1]=="\'":
                word_and_type[1] = word_and_type[1][:-1]

            program_domain_node = ET.SubElement(program_domains_node, 'POGRAM_DOMAIN')
            program_domain_node.set('word', word_and_type[0])
            program_domain_node.set('type', word_and_type[1])

        if comment[6] != comment[6]:
            problem_domains = []
        else:
            problem_domains = comment[6].split(" |||")
            problem_domains = [x.strip() for x in problem_domains]
        problem_domains_node = ET.SubElement(comment_node, "PROBLEM_DOMAINS");
        for problem_domain in problem_domains:
            problem_domain_node = ET.SubElement(problem_domains_node, 'PROBLEM_DOMAIN')
            problem_domain_node.set('word', problem_domain)

    xml_data = ET.tostring(root)
    reparsed = minidom.parseString(xml_data)
    xml_data = reparsed.toprettyxml()
    with open(outputprefix+"_comments.xml",'w') as f:
        f.write(xml_data)

if len(sys.argv) != 5:
    print("Give 4 Arguments: project_name, project_path, file_location, outputprefix")
    exit(-1)

createXML(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
