import sys
import re
import pickle
import argparse
import csv
import nltk
import string
from nltk.corpus import stopwords
import xml.dom.minidom
from xml.dom.minidom import parse
from rdflib import Graph, Literal, BNode, Namespace, RDF, URIRef
from rdflib.namespace import XSD
from collections import defaultdict

g = Graph()
all_name_tokens = set()
all_files = set()

#Defining the prefixes
symbol = Namespace("http://smartKT/ns/symbol#")
prop = Namespace("http://smartKT/ns/properties#")

g.bind("symbol",symbol)
g.bind("prop",prop)

stop_words = set(stopwords.words('english'))
pos_list = ['CC', 'CD', 'DT', 'EX', 'JJR', 'JJS', 'PRP', 'PRP$', '$', 'RB', 'RBR', 'RBS', 'RP', 'WDT', 'WP$', 'WP', 'WRB', 'MD']
word_list = ['definition', 'definitions', 'update', 'updates', 'sequence', 'sequences', 'associated', 'involved', 'accessed', 'invokes', 'invoke', 'are', 'list', 'many']


def camel_to_underscore(match):
    return match.group(1) + "_" + match.group(2)


def tokenise(word):

    REG = r"(.+?)([A-Z])"   #detect CamelCase
    result = re.sub(REG, camel_to_underscore, word, 0)  #substitute every CamelCase with underscore
    result = re.sub(r'[_ ]+','_', result)   #replace multiple spcae or _ with single _
    result = result.split('_')  #split on _ to get tokens

    return list(set(result))


def check_pos_tag(token):

    if nltk.pos_tag([token])[0][1] in pos_list:
        return False
    else:
        if nltk.pos_tag([token])[0][1] == 'JJ':
            if token.find('-') == -1:
                return False

    return True


def add_name_tokens(nodeId,spelling):

    token_list = tokenise(spelling)
    # print(spelling + ':')
    # print(token_list)

    g.add( (symbol[nodeId], prop['name_token'], Literal(spelling)) )

    for token in token_list:
        token = re.sub(r"[=,.;:#?*!&$'\"\"\)\(\[\]\\\/\++]", "", token)
        if (len(token)>2) and token not in stop_words and token not in string.punctuation and token!='' and check_pos_tag(token) and (token not in word_list):
            all_name_tokens.add(token)
            g.add( (symbol[nodeId], prop['name_token'], Literal(token)) )


def get_id(nodeId):

    while nodeId and nodeId != mapping_extra_id[nodeId]:
        nodeId = mapping_extra_id[nodeId]

    return nodeId


def add_static_var_triple(node,parent_node):

    nodeId = str(node.getAttribute("id"))
    nodeId = get_id(nodeId)

    if(node.tagName == "VarDecl" and parent_node.tagName == "ClassDecl"):
        g.add( (symbol[nodeId], prop['is_static'], Literal("True")) )


def add_multi_inheritance(nodeId):
    g.add( (symbol[nodeId], prop['multiple_inheritance'], Literal("True")) )


def add_subclass_triple(nodeId,ParentId):

    g.add( (symbol[ParentId], prop['is_subclass_of'], symbol[nodeId]) )


def add_function_type_triple(nodeId,signature):

    params = list()

    if signature.find('(')!=-1:

        return_type = signature.split("(")[0].strip()
        g.add( (symbol[nodeId], prop['return_type'], Literal(return_type)) )

        string = signature.split("(")[1].strip()
        params = string.split(",")

        for param in params:
            param = param.replace(")","")

            g.add( (symbol[nodeId], prop['param_type'], Literal(param)) )


def add_array_triple(nodeId,array_type):

    obj = re.findall(r'\[.*?\]',array_type)

    if len(obj) > 1:
        g.add( (symbol[nodeId], prop['is_multi_dimensional_array'], Literal("True")) )
    # else:
    #     g.add( (symbol[nodeId], prop['is_single_dimensional_array'], Literal("True")) )

    g.add( (symbol[nodeId], prop['is_array'], Literal("True")) )

    obj=''.join(obj)

    g.add( (symbol[nodeId], prop['array_size'], Literal(obj)) )


def add_pointer_triple(nodeId,obj):

    g.add( (symbol[nodeId], prop['is_pointer'], Literal("True")) )


def add_all_triples(node,parent_node,current_file_seen):

    nodeId = str(node.getAttribute("id"))
    ParentId = str(parent_node.getAttribute("id"))

    ParentId = get_id(ParentId)
    nodeId = get_id(nodeId)

    allAttributes = node.attributes.items()
    global unique_file_seen
    fileName = ''
    inherit_kind = ''
    isDECL = False
    isDEF = False

    for attribute in allAttributes:
        subj = str(attribute[0])
        obj = str(attribute[1])

        if subj == "size":
            g.add( (symbol[nodeId], prop[subj], Literal(obj,datatype=XSD.integer)) )

        if subj == "file":
            fileName = obj
            add_filename_triple(nodeId,fileName)

        if subj == "isDecl":
            isDECL = obj

        if subj == "isDef":
            isDEF = obj

        if subj == "line":
            line_no = obj

        if subj == "inheritance_kind":
            g.add( (symbol[nodeId], prop[subj], Literal(obj) ) )

        if subj == "isCXXVirtual":
            g.add( (symbol[nodeId], prop["is_virtual"], Literal(obj)) )

        if subj == "isVirtualBase":
            g.add( (symbol[ParentId], prop["is_virtual"], Literal(obj)) )

        if subj == "id":
            temp_id = obj

        if subj == "type":
            if(node.tagName == "FunctionDecl" or node.tagName == "CXXMethod"):
                add_function_type_triple(nodeId,obj)
            else:
                if obj.find('[')!=-1:
                    add_array_triple(nodeId,obj)
                elif obj.find('*')!=-1:
                    add_pointer_triple(nodeId,obj)
                g.add( (symbol[nodeId], prop[subj], Literal(obj)) )

        if subj == "spelling" or subj == "access_specifier" or subj == "usr" or subj == "linkage_kind" or subj == "storage_class" or subj == "mangled_name" or subj == "linkage_name":
            g.add( (symbol[nodeId], prop[subj], Literal(obj)) )

        if subj == "spelling":
            add_name_tokens(nodeId,obj)

        if subj == "lex_parent_id" or subj == "sem_parent_id":
            lex_parent_id = obj
            actual_parent_id = get_id(lex_parent_id)
            g.add( (symbol[nodeId], prop[subj], symbol[actual_parent_id]) )


    if node.tagName == "CXXBaseClassSpecifier":
        add_subclass_triple(nodeId,ParentId)

    file = fileName.split("/")[-1]

    if file in unique_file_seen:
        file = file + '_1'
    else:
        current_file_seen.add(file)

    if isDECL and isDEF:
        g.add( (symbol[nodeId], prop['is_defined_file'], Literal(file)))
        g.add( (symbol[nodeId], prop['has_id'], Literal(temp_id,datatype=XSD.integer)) )

    elif isDECL:
        g.add( (symbol[nodeId], prop['is_extern_file'], Literal(file)))         #just declared not defined

    elif not isDEF and not isDECL:
        g.add( (symbol[nodeId], prop['is_called_file'], Literal(file)))


    add_static_var_triple(node,parent_node)
    add_line_no(nodeId,isDECL,isDEF,fileName,line_no)

    add_parent_triple(nodeId,ParentId)

    add_child_triple(nodeId,ParentId)

    if node.tagName != "UnexposedExpr":
        g.add( (symbol[nodeId], prop['is_a'], Literal(node.tagName)) )


def add_line_no(nodeId,isDECL,isDEF,filename,line_no):

    file_name_list = filename.split("/")

    if len(file_name_list)!=1:
        file_name = file_name_list[-2] + '/' + file_name_list[-1]

        file_line = file_name + '#' + str(line_no)

        if isDECL and isDEF:
            g.add( (symbol[nodeId], prop['isDecl_file_line'], Literal(file_line)) )
            g.add( (symbol[nodeId], prop['isDef_file_line'], Literal(file_line)) )

        elif isDECL:
            g.add( (symbol[nodeId], prop['isDecl_file_line'], Literal(file_line)) )

        elif isDEF:
            g.add( (symbol[nodeId], prop['isDef_file_line'], Literal(file_line)) )

        else:
            g.add( (symbol[nodeId], prop['isUse_file_line'], Literal(file_line)) )


def add_parent_triple(ChildId,ParentId):

    if ParentId and ChildId:
        g.add( (symbol[ChildId], prop['has_parent'], symbol[ParentId]))


def add_child_triple(ChildId,ParentId):

    if ParentId and ChildId:
        g.add( (symbol[ParentId], prop['has_child'], symbol[ChildId]))


def add_filename_triple(nodeId,fileName):

    abs_file = fileName.split("/")[-1]
    all_files.add(abs_file)
    # g.add( (symbol[nodeId], prop['relative_file_path'], Literal(fileName)))
    g.add( (symbol[nodeId], prop['absolute_file_path'], Literal(abs_file)))


def add_written_binary_triple(node):

    file_name_list = node.getAttribute("file").split("/")

    if len(file_name_list) != 1:
        file_name = file_name_list[-2] + '/' + file_name_list[-1]
        nodeId = str(node.getAttribute("id"))
        nodeId = get_id(nodeId)
        line_no = node.getAttribute("line")

        file_line = file_name + '#' + str(line_no)

        g.add( (symbol[nodeId], prop['isWritten_file_line'], Literal(file_line)))


def add_read_binary_triple(node):

    file_name_list = node.getAttribute("file").split("/")

    if len(file_name_list) != 1:
        file_name = file_name_list[-2] + '/' + file_name_list[-1]
        nodeId = str(node.getAttribute("id"))
        nodeId = get_id(nodeId)
        line_no = node.getAttribute("line")

        file_line = file_name + '#' + str(line_no)

        g.add( (symbol[nodeId], prop['isRead_file_line'], Literal(file_line)))


#Assumption is that the first child tag with spelling under BinaryOperator will be the tag which is being written and the rest child tags are being read.
def add_binary_operator_triples(node):

    count = 0
    for child in node.childNodes:
        if child.nodeType != child.TEXT_NODE and child.hasAttribute("spelling"): #since Integer Literals don't have spellings so we don't add triples for them
            if(count==0):
                add_written_binary_triple(child)        #The first child tag with spelling is the one which is being written
                count = 1
            else:
                add_read_binary_triple(child)           #The rest child tags are being read


def add_friend_triples(friend_node):

    ParentId = friend_node.getAttribute("lex_parent_id")
    ParentId = get_id(ParentId)
    nodeId = ''

    for child in friend_node.childNodes:
        if child.nodeType != child.TEXT_NODE:
            if child.tagName == "TypeRef" or child.tagName == "FunctionDecl":
                nodeId = str(child.getAttribute("id"))
                nodeId = get_id(nodeId)
                break

    g.add( (symbol[nodeId], prop['is_friend_of'], symbol[ParentId]) )


def iterate_node(node,current_file_seen):

    child_flag = False
    count = 0

    ParentId = str(node.getAttribute("id"))
    ParentId = get_id(ParentId)

    for child in node.childNodes:
        if child.nodeType != child.TEXT_NODE:
            if child.hasAttribute("spelling"):   #we add triples for only the ones that have spelling attribute
                child_flag = True
                add_all_triples(child,node,current_file_seen)
            if(child.tagName == "BinaryOperator"):
                add_binary_operator_triples(child)
            if(child.tagName == "FriendDecl"):
                add_friend_triples(child)
            if(child.tagName == "CXXBaseClassSpecifier"):
                count += 1

            iterate_node(child,current_file_seen)

    if(count >= 2):
        add_multi_inheritance(ParentId)



if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Files needed to run the code.')

    #Input
    parser.add_argument(dest='XMLFile', action='store', help='Input the Static XML file path')
    parser.add_argument(dest='PICKLEFile', action='store', help='Input the PICKLE file path')

    #Output
    parser.add_argument(dest='TTLFile', action='store', help='File path to store the generated TTL')
    parser.add_argument(dest='NameTokensCSV', action='store', help='File path to store the named tokens')
    parser.add_argument(dest='NameTokensPkl', action='store', help='File path to store the named tokens')
    parser.add_argument(dest='Files', action='store', help='File path to store the list of files')

    args = vars(parser.parse_args())
    XMLfile = args['XMLFile']
    TTLFile = args['TTLFile']
    PICKLEFile = args['PICKLEFile']

    mapping_extra_id = pickle.load( open( PICKLEFile, "rb" ) )

    DOMTree = xml.dom.minidom.parse(XMLfile)
    collection = DOMTree.documentElement

    unique_file_seen = set()

    files = collection.getElementsByTagName("TranslationUnit")

    for file in files:
        current_file_seen = set()
        iterate_node(file,current_file_seen)
        unique_file_seen = unique_file_seen | current_file_seen
        # print(unique_file_seen)

    g.serialize(TTLFile,format='ttl')

    with open(args['NameTokensCSV'], 'w') as myfile:
        wr = csv.writer(myfile, delimiter = '\n')
        wr.writerow(list(all_name_tokens))

    pickle.dump( all_name_tokens, open(args['NameTokensPkl'], "wb" ) )
    pickle.dump( all_files, open(args['Files'], "wb"))


'''
python execution cmd : python parseXMLnew.py -h (to see the arguments reqd)
python parseStaticXML.py ../../xml_csv_files/libpng_xml/final_static.xml ../../TTL\ files/libpng\ TTL/final_static.ttl ../../Data\ files/mapping_libpng_static.p


'''
