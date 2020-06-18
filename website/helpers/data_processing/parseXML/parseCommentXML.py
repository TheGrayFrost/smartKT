#This code parses the comments.xml file and creates the corresponding smartKTcomment.ttl file.
# Usgae: python3 parseCommentXML.py <all_store.p>

import sys, nltk, numpy as np
import xml.dom.minidom
from xml.dom.minidom import parse
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from rdflib import Graph, Literal, BNode, Namespace, RDF, URIRef
from rdflib.namespace import XSD
import argparse, re, pickle, string, csv
from importlib import reload as reload

DEBUG = False

g = Graph()
all_comment_tokens = list()

reload(sys)

all_store = None

# print(len(all_store['problem_domain']))

stop_words = set(stopwords.words('english'))
pos_list = ['CC', 'CD', 'DT', 'EX', 'JJR', 'JJS', 'PRP', 'PRP$', '$', 'RB', 'RBR', 'RBS', 'RP', 'WDT', 'WP$', 'WP', 'WRB', 'MD']
word_list = ['definition', 'definitions', 'update', 'updates', 'sequence', 'sequences', 'associated', 'involved', 'accessed', 'invokes', 'invoke', 'are', 'list']

#Defining the prefixes
symbol = Namespace("http://smartKT/ns/symbol#")
comment = Namespace("http://smartKT/ns/comment#")
prop = Namespace("http://smartKT/ns/properties#")

g.bind("symbol",symbol)
g.bind("comment",comment)
g.bind("prop",prop)

def get_id(nodeId):

    while nodeId and nodeId != mapping_extra_id[nodeId]:
        nodeId = mapping_extra_id[nodeId]

    return nodeId


def check_token(token):

    ans = True

    for attr in all_store:
        for key in all_store[attr]:
            if re.match(str(token),str(key), re.IGNORECASE):
                return False

    return ans


def check_pos_tag(token):

    if nltk.pos_tag([token])[0][1] in pos_list:
        return False
    else:
        if nltk.pos_tag([token])[0][1] == 'JJ':
            if token.find('-') == -1:
                return False

    return True


def add_comment_tokens(commentId,text):

    token_list = text.split()
    new_token_list = list()

    for token in token_list:
        if token not in stop_words and token not in string.punctuation:
            token = token.strip('-').lower()
            token = re.sub(r"[=,.;:#?*!&$'\"\"\)\(\[\]\\\/\++]", "", token)
            if not token.isdigit():
                if token != "==" and len(token)>2 and check_token(token) and check_pos_tag(token) and (token not in word_list):
                    if nltk.pos_tag([token])[0][1] == 'JJ':
                        jj_list = token.split('-')
                        for new_tokens in jj_list:
                            new_tokens = new_tokens.strip('-').lower()
                            if (not new_tokens.isdigit()) and len(new_tokens)>2 and check_token(new_tokens) and check_pos_tag(new_tokens) and (new_tokens not in stop_words) and (new_tokens not in string.punctuation) and (new_tokens not in word_list):
                                if DEBUG:
                                    print('jj: '+new_tokens)
                                new_token_list.append(new_tokens)
                                g.add( (comment[commentId], prop['comment_token'], Literal(new_tokens)) )
                    else:
                        new_token_list.append(token)
                        if DEBUG:
                            print(token)
                        g.add( (comment[commentId], prop['comment_token'], Literal(token)) )

    return new_token_list


#This function adds triples for a comment where information is taken from the attributes in COMMENT tag.
def addCommentTriples(commentId,allAttributes):

    g.add( (comment[commentId], prop['has_id'], Literal(commentId,datatype=XSD.integer)) )
    comment_text = ''

    for each in allAttributes:
        subj = str(each[0])
        obj = str(each[1])

        if(subj == "comment_text"):
            g.add( (comment[commentId], prop['text'], Literal(obj)) )
            comment_text = obj
        if(subj == "src_file_location"):
            abs_filename = obj.split("/")[-1]
            g.add( (comment[commentId], prop['is_defined_file'], Literal(abs_filename)) )

    token_list = add_comment_tokens(commentId,comment_text)
    all_comment_tokens.extend(token_list)

    return token_list


#This function adds triples for all the variables under the SYMBOLS tag and the infromation added are the words from PROBLEM_DOMAIN tags.
def addTriples(symbols,commentId,problemDomainWords,token_list):

    for child in symbols.childNodes:
        if(child.nodeType != child.TEXT_NODE):
            nodeId = str(child.getAttribute("id"))
            nodeId = get_id(nodeId)
            g.add( (symbol[nodeId], prop['comment_id'], comment[commentId]))
            for word in problemDomainWords:
                g.add( (symbol[nodeId], prop['PROBLEM_DOMAIN'], Literal(word)) )
            for token in token_list:
                g.add( (symbol[nodeId], prop['comment_token'], Literal(token)) )


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Files needed to run the code.')
    # Inputs
    parser.add_argument(dest='AllStore', action='store', help='Input the AllStore file path')
    parser.add_argument(dest='XMLFile', action='store', help='Input the Comment XML file path')
    parser.add_argument(dest='PICKLEFile', action='store', help='Input the PICKLE file path')

    # Outputs
    parser.add_argument(dest='TTLFile', action='store', help='File path to store the generated TTL')
    parser.add_argument(dest='CommentTokenTaggedCSV', action='store', help='File path to store the comments tokens tagged in csv')
    parser.add_argument(dest='CommentTokensCSV', action='store', help='File path to store the comments tokens in csv')
    parser.add_argument(dest='CommentTokensPkl', action='store', help='File path to store the comments tokens in PKL')

    args = vars(parser.parse_args())
    all_store = pickle.load(open(args['AllStore'], "rb"))
    XMLfile = args['XMLFile']
    TTLFile = args['TTLFile']
    PICKLEFile = args['PICKLEFile']

    mapping_extra_id = pickle.load( open( PICKLEFile, "rb" ) )

    DOMTree = xml.dom.minidom.parse(XMLfile)
    collection = DOMTree.documentElement

    comments = collection.getElementsByTagName("COMMENT")

    for com in comments:
        commentId = str(com.getAttribute("comment_id"))
        allAttributes = com.attributes.items()
        token_list = addCommentTriples(commentId,allAttributes)

        problemDomainList = com.getElementsByTagName("PROBLEM_DOMAINS")
        problemDomainWords = list()

        for problemDomain in problemDomainList:
            for child in problemDomain.childNodes:
                if(child.nodeType != child.TEXT_NODE and (child.tagName == "PROBLEM_DOMAIN")):
                    problemDomainWords.append(child.getAttribute("word"))

        symbols = com.getElementsByTagName("SYMBOLS")

        for sym in symbols:
            addTriples(sym,commentId,problemDomainWords,token_list)

    g.serialize(TTLFile,format='ttl')

    all_comment_tokens = list(set(all_comment_tokens))
    all_tagged_comment_tokens = nltk.pos_tag(all_comment_tokens)

    if DEBUG:
        print(all_comment_tokens)

    with open(args['CommentTokenTaggedCSV'], 'w') as myfile:
        wr = csv.writer(myfile, delimiter = '\n')
        wr.writerow(all_tagged_comment_tokens)

    with open(args['CommentTokensCSV'], 'w') as myfile:
        wr = csv.writer(myfile, delimiter = '\n')
        wr.writerow(all_comment_tokens)

    pickle.dump(all_comment_tokens, open( args['CommentTokensPkl'], "wb" ))
