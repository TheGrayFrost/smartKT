# Usage:
# python3 <static_XML> <comment_XML> <output_file>

import nltk, pickle, sys
import xml.dom.minidom
from xml.dom.minidom import parse
from nltk.stem import WordNetLemmatizer
from collections import defaultdict

keys = ['symbol', 'static_attribute', 'dynamic_attribute', 'problem_domain', 'common_word', 'values']
all_store = {key: {} for key in keys}

for key in keys:
    all_store[key] = defaultdict(set)

#common_word stores a set of tags corresponding to every word which can commonly be used
#symbol stores a set of tags corresponding to every symbol name
#values stores a set of values corresponding to some static attributes


#mapping these words in the query to their respective tags in TTL
def add_common_words_to_tags():

    # all_store['common_word'] = defaultdict(list)
    all_store['common_word']['variable'] = set(['FieldDecl', 'ParmDecl', 'VarDecl', 'EnumDecl', 'StructDecl', 'UnionDecl'])
    all_store['common_word']['Variable'] = set(['FieldDecl', 'ParmDecl', 'VarDecl', 'EnumDecl', 'StructDecl', 'UnionDecl'])
    all_store['common_word']['Variables'] = set(['FieldDecl', 'ParmDecl', 'VarDecl', 'EnumDecl', 'StructDecl', 'UnionDecl'])
    all_store['common_word']['datastructure'] = set(['FieldDecl', 'ParmDecl', 'VarDecl', 'EnumDecl', 'StructDecl', 'UnionDecl'])
    all_store['common_word']['item'] = set(['FieldDecl', 'ParmDecl', 'VarDecl', 'EnumDecl', 'StructDecl', 'UnionDecl'])
    all_store['common_word']['instance'] = set(['FieldDecl', 'ParmDecl', 'VarDecl', 'EnumDecl', 'StructDecl', 'UnionDecl'])
    all_store['common_word']['field'] = set(['FieldDecl', 'ParmDecl', 'VarDecl', 'EnumDecl', 'StructDecl', 'UnionDecl'])
    all_store['common_word']['composite datastructure'] = set(['FieldDecl', 'ParmDecl', 'VarDecl', 'EnumDecl', 'StructDecl', 'UnionDecl'])
    all_store['common_word']['var'] = set(['FieldDecl', 'ParmDecl', 'VarDecl', 'EnumDecl', 'StructDecl', 'UnionDecl'])
    all_store['common_word']['variables'] = set(['FieldDecl', 'ParmDecl', 'VarDecl', 'EnumDecl', 'StructDecl', 'UnionDecl'])
    all_store['common_word']['member variables'] = set(['FieldDecl', 'ParmDecl', 'VarDecl', 'EnumDecl', 'StructDecl', 'UnionDecl'])
    all_store['common_word']['parameters'] = set(['ParmDecl'])
    all_store['common_word']['parameter'] = set(['ParmDecl'])
    all_store['common_word']['fields'] = set(['FieldDecl', 'ParmDecl', 'VarDecl', 'EnumDecl', 'StructDecl', 'UnionDecl'])
    all_store['common_word']['Fields'] = set(['FieldDecl', 'ParmDecl', 'VarDecl', 'EnumDecl', 'StructDecl', 'UnionDecl'])
    all_store['common_word']['Field'] = set(['FieldDecl', 'ParmDecl', 'VarDecl', 'EnumDecl', 'StructDecl', 'UnionDecl'])

    all_store['common_word']['friend'] = set(['FriendDecl'])
    all_store['common_word']['class'] = set(['ClassDecl'])
    all_store['common_word']['classes'] = set(['ClassDecl'])
    all_store['common_word']['structures'] = set(['StructDecl'])

    all_store['common_word']['method'] = set(['FunctionDecl', 'CXXMethod' , 'CXXConstructor'])
    all_store['common_word']['function'] = set(['FunctionDecl', 'CXXMethod' , 'CXXConstructor'])
    all_store['common_word']['Function'] = set(['FunctionDecl', 'CXXMethod' , 'CXXConstructor'])
    all_store['common_word']['Functions'] = set(['FunctionDecl', 'CXXMethod' , 'CXXConstructor'])
    all_store['common_word']['routine'] = set(['FunctionDecl', 'CXXMethod' , 'CXXConstructor'])
    all_store['common_word']['computation unit'] = set(['FunctionDecl', 'CXXMethod' , 'CXXConstructor'])
    all_store['common_word']['functions'] = set(['FunctionDecl', 'CXXMethod' , 'CXXConstructor'])
    all_store['common_word']['constructor'] = set(['FunctionDecl', 'CXXMethod' , 'CXXConstructor'])
    all_store['common_word']['destructor'] = set(['FunctionDecl', 'CXXMethod' , 'CXXConstructor'])
    all_store['common_word']['initialiser'] = set(['FunctionDecl', 'CXXMethod' , 'CXXConstructor'])
    all_store['common_word']['member method'] = set(['FunctionDecl', 'CXXMethod' , 'CXXConstructor'])
    all_store['common_word']['func'] = set(['FunctionDecl', 'CXXMethod' , 'CXXConstructor'])
    all_store['common_word']['methods'] = set(['FunctionDecl', 'CXXMethod' , 'CXXConstructor'])
    all_store['common_word']['constructors'] = set(['FunctionDecl', 'CXXMethod' , 'CXXConstructor'])
    all_store['common_word']['local variable'] = set(['FieldDecl', 'ParmDecl'])
    all_store['common_word']['local variables'] = set(['FieldDecl', 'ParmDecl'])
    all_store['common_word']['global variable'] = set(['VarDecl', 'EnumDecl', 'StructDecl', 'UnionDecl'])
    all_store['common_word']['global variables'] = set(['VarDecl', 'EnumDecl', 'StructDecl', 'UnionDecl'])


def add_synonyms():

        # all_store['concept']['sorting'] = set([('sort','Common Sorting/ Searching/ Traversal Algorithms')])       #how to  use these classes in our TTL
        # all_store['concept']['sort'] = set([('sort','Common Sorting/ Searching/ Traversal Algorithms')])

        all_store['static_attribute']['datatype'] = set(['type'])
        all_store['static_attribute']['primitive data type'] = set(['type'])
        all_store['static_attribute']['data type'] = set(['type'])
        all_store['static_attribute']['primitive type'] = set(['type'])
        all_store['static_attribute']['abstract type'] = set(['type'])
        all_store['static_attribute']['datatype'] = set(['type'])
        all_store['static_attribute']['signature'] = set(['type'])

        all_store['static_attribute']['name'] = set(['spelling'])
        all_store['static_attribute']['multiple inheritance'] = set(['multiple_inheritance'])
        all_store['static_attribute']['parameter types'] = set(['param_type'])

        all_store['static_attribute']['defined'] = set(['is_defined_file'])
        all_store['static_attribute']['defined in'] = set(['is_defined_file'])
        all_store['static_attribute']['defined file'] = set(['is_defined_file'])
        all_store['static_attribute']['defined'] = set(['is_defined_file'])
        all_store['static_attribute']['present'] = set(['is_defined_file'])
        all_store['static_attribute']['belongs to'] = set(['is_defined_file'])

        all_store['static_attribute']['start line'] = set(['isDef_file_line'])

        all_store['static_attribute']['called'] = set(['is_called_file'])
        all_store['static_attribute']['called in'] = set(['is_called_file'])
        all_store['static_attribute']['invoked'] = set(['is_called_file'])
        all_store['static_attribute']['call'] = set(['is_called_file'])
        all_store['static_attribute']['call expression'] = set(['is_called_file'])
        all_store['static_attribute']['called'] = set(['is_called_file'])

        all_store['static_attribute']['definition and use'] = set(['isUse_file_line'])

        all_store['static_attribute']['input parameter'] = set(['param_type'])
        all_store['static_attribute']['input parameter of type'] = set(['param_type'])
        all_store['static_attribute']['parameter'] = set(['param_type'])

        all_store['static_attribute']['storage class'] = set(['storage_class'])
        all_store['static_attribute']['scope'] = set(['storage_class'])
        all_store['static_attribute']['visibility'] = set(['storage_class'])

        all_store['static_attribute']['parent'] = set(['has_parent'])
        all_store['static_attribute']['predecessor'] = set(['has_parent'])
        all_store['static_attribute']['parent function'] = set(['has_parent'])

        all_store['static_attribute']['child'] = set(['has_child'])
        all_store['static_attribute']['successor'] = set(['has_child'])
        all_store['static_attribute']['descendant'] = set(['has_child'])

        all_store['static_attribute']['return value'] = set(['return_type'])
        all_store['static_attribute']['return'] = set(['return_type'])
        all_store['static_attribute']['return type'] = set(['return_type'])

        all_store['static_attribute']['friend of'] = set(['is_friend_of'])
        all_store['static_attribute']['friend class'] = set(['is_friend_of'])
        all_store['static_attribute']['friend function'] = set(['is_friend_of'])

        all_store['static_attribute']['child class'] = set(['is_subclass_of'])
        all_store['static_attribute']['subclass'] = set(['is_subclass_of'])

        all_store['static_attribute']['comment'] = set(['comment_token'])
        all_store['static_attribute']['comments'] = set(['comment_token'])

        all_store['static_attribute']['application domain'] = set(['PROBLEM_DOMAIN'])
        all_store['static_attribute']['task specific'] = set(['PROBLEM_DOMAIN'])
        all_store['static_attribute']['application task'] = set(['PROBLEM_DOMAIN'])
        all_store['static_attribute']['application specific'] = set(['PROBLEM_DOMAIN'])
        all_store['static_attribute']['target application'] = set(['PROBLEM_DOMAIN'])

        all_store['static_attribute']['accessed'] = set(['is_called_file'])
        all_store['static_attribute']['used'] = set(['is_called_file'])

        all_store['static_attribute']['may be read'] = set(['isRead_file_line'])
        all_store['static_attribute']['possibly read'] = set(['isRead_file_line'])
        all_store['static_attribute']['possibly written'] = set(['isWritten_file_line'])
        all_store['static_attribute']['may be written'] = set(['isWritten_file_line'])
        all_store['static_attribute']['possible read-write'] = set(['isRead_file_line','isWritten_file_line'])

        all_store['static_attribute']['pointers'] = set(['is_pointer'])
        all_store['static_attribute']['pointer'] = set(['is_pointer'])

        all_store['static_attribute']['arrays'] = set(['is_array'])
        all_store['static_attribute']['array'] = set(['is_array'])
        all_store['static_attribute']['size array'] = set(['array_size'])
        all_store['static_attribute']['multidimensional arrays'] = set(['is_multi_dimensional_array'])

        all_store['dynamic_attribute']['read'] = set(['NONLOCALREAD','read_count'])

        all_store['dynamic_attribute']['written'] = set(['write_count','NONLOCALWRITE'])
        all_store['dynamic_attribute']['updated'] = set(['write_count','NONLOCALWRITE'])
        all_store['dynamic_attribute']['update'] = set(['write_count','NONLOCALWRITE'])
        all_store['dynamic_attribute']['write'] = set(['write_count','NONLOCALWRITE'])

        all_store['dynamic_attribute']['read-write'] = set(['NONLOCALREAD','read_count','write_count','NONLOCALWRITE'])
        all_store['dynamic_attribute']['read write'] = set(['NONLOCALREAD','read_count','write_count','NONLOCALWRITE'])

        all_store['dynamic_attribute']['thread id'] = set(['thread_id'])
        all_store['dynamic_attribute']['thread number'] = set(['thread_id'])
        all_store['dynamic_attribute']['thread'] = set(['thread_id'])
        all_store['dynamic_attribute']['threads'] = set(['thread_id'])
        all_store['dynamic_attribute']['thread access'] = set(['thread_id'])

        all_store['dynamic_attribute']['synchronous'] = set(['sync'])
        all_store['dynamic_attribute']['unsynchronised'] = set(['sync'])
        all_store['dynamic_attribute']['asynchronised'] = set(['sync'])
        all_store['dynamic_attribute']['synchronised'] = set(['sync'])
        all_store['dynamic_attribute']['unsynchronized'] = set(['sync'])
        all_store['dynamic_attribute']['asynchronized'] = set(['sync'])
        all_store['dynamic_attribute']['synchronized'] = set(['sync'])
        all_store['dynamic_attribute']['unsynchronous'] = set(['sync'])
        all_store['dynamic_attribute']['asynchronous'] = set(['sync'])

        all_store['dynamic_attribute']['mutex'] = set(['posix_lock'])

        all_store['dynamic_attribute']['callee'] = set(['callee_name'])
        all_store['dynamic_attribute']['invoked'] = set(['callee_name'])
        all_store['dynamic_attribute']['called'] = set(['callee_name'])
        all_store['dynamic_attribute']['child function'] = set(['callee_name'])
        all_store['dynamic_attribute']['call graph'] = set(['callee_name'])
        all_store['dynamic_attribute']['function call graph'] = set(['callee_name'])
        all_store['dynamic_attribute']['call sequence'] = set(['callee_name'])
        all_store['dynamic_attribute']['invocation sequence'] = set(['callee_name'])
        all_store['dynamic_attribute']['invocation graph'] = set(['callee_name'])

        all_store['dynamic_attribute']['invoker'] = set(['caller_name'])
        all_store['dynamic_attribute']['caller'] = set(['caller_name'])


#adding problem domain words
def parse_comment_XMLFile(commentXML):

    DOMTree = xml.dom.minidom.parse(commentXML)
    collection = DOMTree.documentElement

    comments = collection.getElementsByTagName("COMMENT")

    for com in comments:
        problemDomainList = com.getElementsByTagName("PROBLEM_DOMAINS")
        for problem_domain in problemDomainList:
            for child in problem_domain.childNodes:
                if(child.nodeType != child.TEXT_NODE and (child.tagName == "PROBLEM_DOMAIN")):
                    word = child.getAttribute("word")
                    all_store['problem_domain'][word].add(word)


#adding dynamic attributes
def parse_dynamic_XMLFile():

    all_store['dynamic_attribute']['thread-id'] = set(['THREADID'])
    all_store['dynamic_attribute']['synchronous'] = set(['SYNCS'])
    all_store['dynamic_attribute']['read count'] = set(['READCOUNT'])
    all_store['dynamic_attribute']['write count'] = set(['WRITECOUNT'])
    all_store['dynamic_attribute']['return value'] = set(['RETVAL'])
    all_store['dynamic_attribute']['CALLEENAME'] = set(['CALLEENAME'])
    all_store['dynamic_attribute']['CALLERNAME'] = set(['CALLERNAME'])


#adding function names, file names, var names as symbols and adding static attributes
def parse_static_XMLFile(staticXML):

    funcList = list()
    varList = list()

    DOMTree = xml.dom.minidom.parse(staticXML)
    collection = DOMTree.documentElement

    files = collection.getElementsByTagName("TranslationUnit")

    for file in files:
        #all function names and class names to be added in symbol
        funcList = file.getElementsByTagName('FunctionDecl')        #file.getElementsByTagName('FUNCTION_DECL') returns a list of all function instances in that file.
        funcList.extend(file.getElementsByTagName('CXXMethod'))
        funcList.extend(file.getElementsByTagName('CXXConstructor'))
        funcList.extend(file.getElementsByTagName('ClassDecl'))

        #all variable names to be added in symbol
        varList = file.getElementsByTagName('FieldDecl')
        varList.extend(file.getElementsByTagName('ParmDecl'))
        varList.extend(file.getElementsByTagName('VarDecl'))
        varList.extend(file.getElementsByTagName('EnumDecl'))
        varList.extend(file.getElementsByTagName('StructDecl'))
        varList.extend(file.getElementsByTagName('UnionDecl'))

        add_functions(funcList)
        add_variables(varList)


def add_values(attribute):

    if str(attribute[0]) == 'type' or str(attribute[0]) == "storage_class" or str(attribute[0]) == "access_specifier" or str(attribute[0]) == 'return_type':
        all_store['values'][str(attribute[1])].add(str(attribute[0]))


#add static attributes as symbol in the dictionary
def add_static_attributes(function):

    allAttributes = function.attributes.items()
    for attribute in allAttributes:
        if str(attribute[0]) != 'file':
            all_store['static_attribute'][str(attribute[0])].add(str(attribute[0]))
            add_values(attribute)


#add variable names as symbol in the dictionary
def add_variables(varList):

    for var in varList:
        varName = str(var.getAttribute("spelling"))
        fileName = str(var.getAttribute("file"))
        fileName = fileName.split("/")[-1]
        all_store['symbol'][varName].add(var.tagName)

        add_static_attributes(var)


#add function names as symbol in the dictionary
def add_functions(funcList):

    for func in funcList:
        funcName = str(func.getAttribute("spelling"))
        fileName = str(func.getAttribute("file"))
        fileName = fileName.split("/")[-1]
        all_store['symbol'][funcName].add(func.tagName)

        add_static_attributes(func)

staticXML = sys.argv[1]
commentXML = sys.argv[2]

parse_static_XMLFile(staticXML)
parse_dynamic_XMLFile()
parse_comment_XMLFile(commentXML)

# populate_concepts(conceptsFile)
add_synonyms()
add_common_words_to_tags()


pickle.dump(all_store, open(sys.argv[3], "wb" ) )

# python all_store.py ../xml_csv_files/libpng_xml/final_static.xml ../xml_csv_files/libpng_xml/final_comments.xml
