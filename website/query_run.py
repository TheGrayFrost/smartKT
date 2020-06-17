import sys
from importlib import reload as reload
import re
import nltk
import string
import argparse
import rdflib
import time
import xml.dom.minidom
from xml.dom.minidom import parse
from rdflib import Graph, Literal, BNode, Namespace, RDF, URIRef
from rdflib.namespace import XSD
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import mapper
from mapper import CreateLists
import itertools
from itertools import permutations
from collections import defaultdict
from collections import OrderedDict
import pickle
from nltk.stem import PorterStemmer

reload(sys)

nltk.download('punkt')
nltk.download('stopwords')
ps = PorterStemmer()

keys = ['symbol', 'name_token']
prev_symbol_list = {key: [] for key in keys}
curr_symbol_list = {key: [] for key in keys}

class QueryConversion:

    def __init__(self,all_store_pickle,all_files_pickle,name_tokens_pickle,comment_tokens_pickle,program_domain_pickle,tf_idf_name_tokens_pickle,tf_idf_symbols_pickle):

        self.all_store = pickle.load( open( all_store_pickle, "rb" ) )
        self.all_files = pickle.load( open( all_files_pickle, "rb"))
        self.all_name_tokens_dict = pickle.load( open( name_tokens_pickle, "rb" ) )     #name_tokens_similarity dictionary
        self.all_comment_tokens_dict = pickle.load( open( comment_tokens_pickle, "rb" ) )   #comment_tokens similarity dictionary
        self.program_domain_dict = pickle.load( open( program_domain_pickle , "rb"))
        self.tf_idf_name_tokens = pickle.load( open( tf_idf_name_tokens_pickle, "rb" ) )
        self.tf_idf_symbol = pickle.load( open( tf_idf_symbols_pickle, "rb" ) )
        self.conflict_flag = False
        self.array_flag = False
        self.pointer_flag = False
        self.grep_flag = False
        self.conflict_words = set()
        self.syntax_count = 0
        self.mapping = {
                        0:self.template_value_common_symbol,
                        1:self.template_value_common_dynamic_attr_file,
                        2:self.template_value_common_file,
                        3:self.template_attr_common_symbol,
                        4:self.template_common_symbol_comment,
                        5:self.template_dynamic_attr_common_symbol_file,
                        6:self.template_dynamic_attr_file,
                        7:self.template_dynamic_attr_common_symbol_common_symbol,
                        8:self.template_dynamic_attr_common_symbol,
                        9:self.template_dynamic_attr_common_comment_token,
                        10:self.template_dynamic_attr_common,
                        11:self.template_common_file,
                        12:self.template_common_symbol,
                        13:self.template_attr_symbol,
                        14:self.template_value_common,
                        15:self.template_comment_common,
                        16:self.template_symbol,
                        17:self.template_common_word,
                        18:self.template_comment_token,
                        19:self.template_name_token,
                        20:self.template_static_attribute,
                        21:self.template_values
                        }
        '''
        all_store is a dictionary with keys as 'symbol', 'attribute' etc extracted from the xml files.

        all_store
        {
            symbol : { png.h : file, inflatePrime : function}
            attribute : { type : type, name : name}
        }
        '''

    #run the function in the file "mapper.py" where we make list of regexes.
    def make_list(self,RegexFile):

        mapperObj = CreateLists()
        all_regex = mapperObj.createRegexList(RegexFile)

        return all_regex


    #removes stopwords and punctuations from the query and returns the new query
    def filter_query_words(self,query):

        stop_words = set(stopwords.words('english'))
        new_query = ''

        tokenize_query = word_tokenize(query)

        for word in tokenize_query:
            if word not in stop_words:
                word = re.sub(r"[,;@#?!&$'\"\"]+\ *", "", word)    #remove any punctuation from the words
                if len(word)!=1 and word!='list' and word!='List':
                    if word == "array" or word == "arrays":
                        self.array_flag = True
                    if word == "pointer" or word == "pointers":
                        self.pointer_flag = True
                    if word == "grep":
                        self.grep_flag = True
                        continue
                    new_query = new_query + word + ' '

        return new_query.strip()                                    #new_query consists of no stopwords and punctuations.


    #return a suffix list of words in the new query
    def create_suffix(self,query):

        tokenize_query = word_tokenize(query)
        suffix_list = list()
        temp = ''

        for word in tokenize_query[::-1]:
            temp = word + ' ' + temp
            suffix_list.append(temp.strip())

        return suffix_list


    #return a prefix list of words in the suffix list
    def create_prefix(self,suffix_list):

        prefix_list = list()

        for suffixes in suffix_list:
            tokenize_query = word_tokenize(suffixes)
            temp = ''

            for word in tokenize_query:
                temp = temp + word + ' '
                prefix_list.append(temp.strip())

        return prefix_list


    #searches for the keywords of the query in the all_store and other dictionaries and store the matched words with their information in word_store
    def search_matched_words(self,query):

        global prev_symbol_list
        global curr_symbol_list
        curr_symbol_list = {key: [] for key in keys}

        word_store = defaultdict(list)
        symbol_list = list()
        search_symbol = False
        search_common_word = False
        search_name_token = False
        search_comment_token = False
        search_sim_token = False
        search_sim_com_token = False
        search_value = False
        search_attr = False
        search_dyn_attr = False

        comment = ''
        comment_word = ''

        # to capture all possible phrases in the query and match it in our dictionary (e.x return type should be captured and mapped to type)
        suffix_list = self.create_suffix(query)
        words = self.create_prefix(suffix_list)

        #words is a list of all possible query phrases
        # print(words)

        #search for words in the all_store dictionary
        for attr in self.all_store:
            for word in words:
                if word in self.all_store[attr]:
                    word_store[attr].append((word,word))
                    if attr == 'symbol':
                        search_symbol = True
                        curr_symbol_list['symbol'].append((word,word))
                    if attr == 'common_word':
                        search_common_word = True
                    if attr == 'values':
                        search_value = True
                    if attr == 'static_attribute':
                        search_attr = True
                    if attr == 'dynamic_attribute':
                        search_dyn_attr = True
                if word in self.all_files:
                    word_store['fil'].append((word,word))

        #if symbol not found search for words in the name_token dictionarys keys
        if not search_symbol:
            for word in words:
                for name_token in self.all_name_tokens_dict.keys():
                    if re.match(str(word),str(name_token), re.IGNORECASE) or re.match(str(ps.stem(word)),str(name_token)):
                        search_name_token = True
                        curr_symbol_list['name_token'].append((word,name_token))            #tuple so that "word" can be used for replacing placeholders in query and "name_token" can be used in SPARQL to fire on TTL
                        word_store['name_token'].append((word,name_token))


            #search for words in the similar words of name_token dictionarys keys
            if not search_symbol and not search_name_token:
                for word in words:
                    search_sim_token = False
                    for name_token in self.all_name_tokens_dict.keys():
                        for similar_token in self.all_name_tokens_dict[name_token]:
                            if re.match(str(word),str(similar_token[0]), re.IGNORECASE) or re.match(str(ps.stem(word)),str(similar_token[0])):
                                search_sim_token = True
                                curr_symbol_list['name_token'].append((word,name_token))
                                word_store['name_token'].append((word,name_token))
                                break
                        if search_sim_token:
                            break

        #search for words in the comment_token dictionarys keys if a word matches any comment token then we add all the similar tokens of that token in the word_store
        for word in words:
            flag = False
            temp_set = set()
            temp_comment = set()
            comment = ''
            for comment_token in self.all_comment_tokens_dict.keys():
                if re.match(str(word),str(comment_token), re.IGNORECASE):
                    search_comment_token = True
                    flag = True
                    comment = comment_token
                    word_store['comment_token'].append((word,comment_token))
                    temp_comment.add(comment_token)
                    self.syntax_count += 1

            if flag and not self.grep_flag:
                print('----------')
                print(len(temp_comment))
                print(temp_comment)

                for similar_token in self.all_comment_tokens_dict[comment]:
                    for taken_comment in temp_comment:
                        if taken_comment != similar_token[0] and (str(ps.stem(taken_comment)) != str(ps.stem(similar_token[0]))):
                            temp_set.add((word,similar_token[0]))

                word_store['comment_token'].extend(list(temp_set))


        #This operates when we cldn't hit the comment dictionary key. Then search for all similar words in the entire dictionary and pick the word with highest similar score and return that whole row.
        if not search_comment_token:
            for word in words:
                maxx = -1000
                maxx_word = ''
                flag = False
                temp_set = set()
                for comment_token in self.all_comment_tokens_dict.keys():
                    for similar_token in self.all_comment_tokens_dict[comment_token]:
                        if re.match('\\b'+str(word)+'\\b',str(similar_token[0]), re.IGNORECASE) or re.match('\\b'+str(ps.stem(word))+'\\b',str(similar_token[0])):  #so that 'many' doesn't match 'manytomany' or 'manipul'
                            if float(similar_token[1]) > maxx:
                                maxx = similar_token[1]
                                maxx_word = comment_token
                                search_sim_com_token = True
                                flag = True

                if flag:
                    self.syntax_count = 1
                    word_store['comment_token'].append((word,maxx_word))
                    for similar_token in self.all_comment_tokens_dict[comment]:
                        if maxx_word != similar_token[0] and (str(ps.stem(maxx_word)) != str(ps.stem(similar_token[0]))):
                            temp_set.add((comment_word,similar_token[0]))
                    word_store['comment_token'].extend(list(temp_set))

        if search_sim_com_token:
            word_store['comment_token'] = list(set(word_store['comment_token']))


        ################################################################################ RESOLVING CONFLICTS LOGIC ##########################################################

        #conflict between value and comment token resolved
        if search_value == True and (search_comment_token == True or search_sim_com_token == True):
            index = list()
            for ind1,comment_token in enumerate(word_store['comment_token']):
                for ind2,value in enumerate(word_store['values']):
                    if value[0] == comment_token[0]:
                        index.append(ind1)
                        break

            for ind in sorted(index, reverse=True):
                del word_store['comment_token'][ind]

        #conflict between value and name token resolved
        if search_value == True and (search_name_token == True or search_sim_token == True):
            index = list()
            for ind1,name_token in enumerate(word_store['name_token']):
                for ind2,value in enumerate(word_store['values']):
                    if value[0] == name_token[0]:
                        index.append(ind1)
                        break

            for ind in sorted(index, reverse=True):
                del word_store['name_token'][ind]

        #conflict between common word and comment token resolved
        if search_common_word == True and (search_comment_token == True or search_sim_com_token == True):
            index = list()
            for ind1,comment_token in enumerate(word_store['comment_token']):
                for ind2,value in enumerate(word_store['common_word']):
                    if value[0] == comment_token[0]:
                        index.append(ind1)
                        break

            for ind in sorted(index, reverse=True):
                del word_store['comment_token'][ind]

        #conflict between symbol and comment token resolved
        if search_symbol == True and (search_comment_token == True or search_sim_com_token == True):
            index = list()
            for ind1,comment_token in enumerate(word_store['comment_token']):
                for ind2,symbol in enumerate(word_store['symbol']):
                    if symbol[0] == comment_token[0]:
                        index.append(ind1)
                        break

            for ind in sorted(index, reverse=True):
                del word_store['comment_token'][ind]

        #conflict between attribute and comment token resolved
        if search_attr == True and (search_comment_token == True or search_sim_com_token == True):
            index = list()
            for ind1,comment_token in enumerate(word_store['comment_token']):
                for ind2,symbol in enumerate(word_store['static_attribute']):
                    if symbol[0] == comment_token[0]:
                        index.append(ind1)
                        break

            for ind in sorted(index, reverse=True):
                del word_store['comment_token'][ind]


        #if a word is present as both name_token and comment_token then we consider it as comment_token and raise a conflict flag
        if (search_name_token == True or search_sim_token == True) and (search_comment_token == True or search_sim_com_token == True):
            index = list()
            for ind1,name_token in enumerate(word_store['name_token']):
                for ind2,comment_token in enumerate(word_store['comment_token']):
                    if name_token[0] == comment_token[0]:
                        self.conflict_flag = True
                        self.conflict_words.add(name_token)
                        index.append(ind1)
                        break

            for ind in sorted(index, reverse=True):
                del word_store['name_token'][ind]

        print('Conflict words if any :'+'\n')
        print(self.conflict_words)

        #conflict between attribute and name token resolved
        if search_attr == True and (search_name_token == True or search_sim_token == True):
            index = list()
            for ind1,name_token in enumerate(word_store['name_token']):
                for ind2,symbol in enumerate(word_store['static_attribute']):
                    if symbol[0] == name_token[0]:
                        index.append(ind1)
                        break

            for ind in sorted(index, reverse=True):
                del word_store['name_token'][ind]


        #conflict between dynamic attribute and comment token resolved
        if search_attr == True and (search_name_token == True or search_sim_token == True):
            index = list()
            for ind1,name_token in enumerate(word_store['comment_token']):
                for ind2,symbol in enumerate(word_store['dynamic_attribute']):
                    if symbol[0] == name_token[0]:
                        index.append(ind1)
                        break

            for ind in sorted(index, reverse=True):
                del word_store['comment_token'][ind]


        if search_symbol:
            for symbol in word_store['symbol']:
                if symbol[0] == 'file':
                    word_store['symbol'].remove(symbol)
                    break


        # if len(curr_symbol_list['symbol'])==0 and len(curr_symbol_list['name_token'])==0 and len(word_store['common_word'])==0 and len(word_store['comment_token'])==0 and len(word_store['static_attribute'])!=0:
        #     count = 0
        #     for symbols in prev_symbol_list['symbol']:
        #         word_store['symbol'].append(symbols)
        #         query = query + ' ' + symbols[0]
        #         count += 1

        #     if(count != 2):
        #         for name_tokens in prev_symbol_list['name_token']:
        #             word_store['name_token'].append(name_tokens)
        #             query = query + ' ' + name_tokens[0]
        #             count += 1
        #             if(count == 2):
        #                 break

        print('#########')
        print(self.syntax_count)
        print(word_store['comment_token'])
        return word_store, query, words


    #replaces the matched words of the query with its type that will be matched with regex e.x type -> <<attribute>>
    def insert_placeholders_in_query(self,words,query,word_store):

        words.sort(key=lambda x: len(x.split()), reverse=True)      #we want to check the matching of bigger phrases first

        for word in words:
            for key in word_store:
                for matched_key_names in word_store[key]:
                    if word == matched_key_names[0]:
                        if query.find(word)!= -1:
                            print(key,matched_key_names[0])
                            query = query.replace(matched_key_names[0],'<<'+key+'>>')
                        # else:
                        #     word_store[key].remove(matched_key_names)       #if you cldn't find the word in the query i.e it's replaced

        return query


    #match the query with the regex in the all_regex list
    def regex_match(self,all_regex,query):

        indices = list()

        for index,regex in enumerate(all_regex):
            res = re.findall(regex,query)
            if(res):
                indices.append(index)

        regex_str = (all_regex[indices[0]]).pattern
        match = re.findall('<<',regex_str)

        if len(match) < 3:
            return indices[:2]

        else:
            return indices[:1]



    #call the corresponding template function according to the matched regex
    def call_matched_template_function(self,word_store,matched_regex_list,graph):

        final_ans = ''

        for ind,regex_index in enumerate(matched_regex_list):
            func_name = self.mapping[regex_index]
            print(func_name)
            ans = func_name(word_store,graph)
            # final_ans += 'Result corresponding to Regex %d' % (ind+1) + '\n\n'
            if ans:
                final_ans = final_ans + ans
            else:
                final_ans += 'No results matched here' + '\n'

        return final_ans


    #this is a template function for only values
    def template_values(self,word_store,graph):

        ans = ''
        file_name = ''
        result_dict = defaultdict(dict)

        if 'fil' in word_store:
            for matched_file in word_store['fil']:
                file_name = matched_file[1]
                break

        query_part_1 = """
            PREFIX prop: <http://smartKT/ns/properties#>
            PREFIX symbol: <http://smartKT/ns/symbol#>

            """

        query_part_2 = "SELECT DISTINCT ?id ?pred ?obj"

        query_part_3 = """
                    WHERE
                    {
                        ?id ?pred ?obj ;
            """

        query_part_6 = 'prop:is_defined_file' + ' ' + '"' + file_name + '"' + ';' + '\n'

        query_part_5 = """
            FILTER (?pred IN (prop:storage_class, prop:isDef_file_line, prop:type, prop:spelling, prop:is_a, prop:is_array, prop:array_size, prop:is_pointer, prop:is_subclass_of, prop:is_friend_of, prop:access_specifier) ) .
            }
            """

        query_part_4 = '?pred1 ' + '"' +'%s' %(word_store['values'][0][1]) + '"' + '.'



        if file_name:
            query = query_part_1 + query_part_2 + query_part_3 + query_part_6 + query_part_4 + query_part_5
        else:
            query = query_part_1 + query_part_2 + query_part_3 + query_part_4 + query_part_5

        print(query)
        start_time = time.time()
        result = graph.query(query)
        end_time = time.time()
        print("Time taken to process query",+end_time-start_time)

        prev_id = None
        ans_temp = ''

        for row in result:
            curr_id = row['id'].split('#')[1]
            result_dict[curr_id][str(row['pred'].split('#')[1])] = str(row['obj'])

        for key in result_dict:
            if 'spelling' in result_dict[key]:
                ans += 'Identifier name : ' + result_dict[key]['spelling'] + '\n'
            if 'storage_class' in result_dict[key]:
               ans += 'Storage class : ' + result_dict[key]['storage_class'] + '\n'
            if 'type' in result_dict[key]:
                ans += 'Datatype : ' + result_dict[key]['type'] + '\n'
            if 'isDef_file_line' in result_dict[key]:
                ans += 'Definition file : ' + result_dict[key]['isDef_file_line'] + '\n'
            if 'is_a' in result_dict[key]:
                ans += 'Identifier type : ' + result_dict[key]['is_a'] + '\n'
            if 'is_array' in result_dict[key]:
                ans += 'Is Array : ' + result_dict[key]['is_array'] + '\n'
            if 'is_pointer' in result_dict[key]:
                ans += 'Is Pointer : ' + result_dict[key]['is_pointer'] + '\n'
            if 'access_specifier' in result_dict[key]:
                ans += 'Access Specifier : ' + result_dict[key]['access_specifier'] + '\n'

            ans += '\n'

        return ans

    #this is a template function for only static attributes
    def template_static_attribute(self,word_store,graph):

        ans = ''
        file_name = ''
        no_of_attributes = len(word_store['static_attribute'])
        result_dict = defaultdict(dict)

        if 'fil' in word_store:
            for matched_file in word_store['fil']:
                file_name = matched_file[1]

        query_part_1 = """
            PREFIX prop: <http://smartKT/ns/properties#>
            PREFIX symbol: <http://smartKT/ns/symbol#>

            """

        query_part_2 = "SELECT DISTINCT ?id ?pred ?obj"

        query_part_3 = """
                    WHERE
                    {
                        ?id ?pred ?obj ;
            """

        query_part_6 = 'prop:is_defined_file' + ' ' + '"' + file_name + '"' + ';' + '\n'

        query_part_5 = """
            FILTER (?pred IN (prop:storage_class, prop:isDef_file_line, prop:type, prop:spelling, prop:is_a, prop:is_array, prop:array_size, prop:is_pointer, prop:is_subclass_of, prop:is_friend_of) ) .
            }
            """

        query_part_4 = ''
        count = 0
        for i in range(no_of_attributes-1):
            count += 1
            query_part_4 = query_part_4 + 'prop:%s' + ' ?obj' + str(count) + ';' + '\n'

        query_part_4 = query_part_4 + 'prop:%s' + ' ?obj' + str(count+1) + '.'

        all_attr_list = list()
        all_arguments = list()

        for matched_attr in word_store['static_attribute']:
            attr_word = matched_attr[0]
            all_attr_list.append(list(self.all_store['static_attribute'][attr_word]))

        print(all_attr_list)

        if no_of_attributes == 1:
            for attr_ in all_attr_list:
                for attr_val in attr_:
                    element = (attr_val)
                    all_arguments.append(element)

        else:
            for element in itertools.product(*all_attr_list):   #we did this if a given word matches with multiple static attributes so considering all combinations. ((read-[isRead_file_line,READCOUNT]))
                element = list(element)
                element = tuple(element)
                all_arguments.append(element)

        for arguments in all_arguments:
            if file_name:
                query = query_part_1 + query_part_2 + query_part_3 + query_part_6 + query_part_4 + query_part_5
            else:
                query = query_part_1 + query_part_2 + query_part_3 + query_part_4 + query_part_5
            print(arguments)
            query = query % arguments
            print(query)
            start_time = time.time()
            result = graph.query(query)
            end_time = time.time()
            print("Time taken to process query",+end_time-start_time)

            prev_id = None
            ans_temp = ''

            for row in result:
                curr_id = row['id'].split('#')[1]
                result_dict[curr_id][str(row['pred'].split('#')[1])] = str(row['obj'])


            for key in result_dict:
                if 'spelling' in result_dict[key]:
                    ans += 'Identifier name : ' + result_dict[key]['spelling'] + '\n'
                if 'storage_class' in result_dict[key]:
                   ans += 'Storage class : ' + result_dict[key]['storage_class'] + '\n'
                if 'type' in result_dict[key]:
                    ans += 'Datatype : ' + result_dict[key]['type'] + '\n'
                if 'isDef_file_line' in result_dict[key]:
                    ans += 'Definition file : ' + result_dict[key]['isDef_file_line'] + '\n'
                if 'is_a' in result_dict[key]:
                    ans += 'Identifier type : ' + result_dict[key]['is_a'] + '\n'
                if 'is_array' in result_dict[key]:
                    ans += 'Is Array : ' + result_dict[key]['is_array'] + '\n'
                if 'is_pointer' in result_dict[key]:
                    ans += 'Is Pointer : ' + result_dict[key]['is_pointer'] + '\n'

                ans += '\n'

        ans += '\n'

        return ans

    #this is a template function for only symbol
    def template_symbol(self,word_store,graph):

        ans = ''
        result_dict = defaultdict(dict)

        query = """
            PREFIX prop: <http://smartKT/ns/properties#>
            PREFIX symbol: <http://smartKT/ns/symbol#>

            SELECT DISTINCT ?id ?pred ?obj
            WHERE
            {
                {
                    ?id prop:spelling "%s";
                        ?pred ?obj.
                }
            }
            """

        for ind,matched_tokens in enumerate(word_store['symbol']):

            # firstFile = self.tf_idf_symbol[matched_tokens[1]][0][0]
            # print(firstFile)
            # queryFirst = query % (matched_tokens[1],firstFile,matched_tokens[1],firstFile,matched_tokens[1],firstFile)
            queryFirst = query % (matched_tokens[1])
            print(queryFirst)

            start_time = time.time()
            resultFirst = graph.query(queryFirst)
            end_time = time.time()

            print("Time taken to process query",+end_time-start_time)

            for row in resultFirst:
                curr_id = row['id'].split('#')[1]
                if str(row['pred'].split('#')[1]) not in result_dict[curr_id]:
                    result_dict[curr_id][str(row['pred'].split('#')[1])] = []
                    result_dict[curr_id][str(row['pred'].split('#')[1])].append(str(row['obj']))
                else:
                    result_dict[curr_id][str(row['pred'].split('#')[1])].append(str(row['obj']))


            for key in result_dict:
                if 'spelling' in result_dict[key]:
                    ans += 'Identifier name : ' + result_dict[key]['spelling'][0] + '\n'
                if 'storage_class' in result_dict[key]:
                   ans += 'Storage class : ' + result_dict[key]['storage_class'][0] + '\n'
                if 'type' in result_dict[key]:
                    ans += 'Datatype : ' + result_dict[key]['type'][0] + '\n'
                if 'isDef_file_line' in result_dict[key]:
                    ans += 'Definition file : ' + result_dict[key]['isDef_file_line'][0] + '\n'
                if 'isDecl_file_line' in result_dict[key]:
                    ans += 'Declaration file : ' + result_dict[key]['isDecl_file_line'][0] + '\n'
                if 'isWritten_file_line' in result_dict[key]:
                    ans += 'Written in file : '
                    for val in result_dict[key]['isWritten_file_line'][:-1]:
                        ans += val + ' , ' + '\n'
                    ans += result_dict[key]['isWritten_file_line'][-1] + ' . ' + '\n'
                if 'isRead_file_line' in result_dict[key]:
                    ans += 'Read in file : '
                    for val in result_dict[key]['isRead_file_line'][:-1]:
                        ans += val + +' , ' + '\n'
                    ans += result_dict[key]['isRead_file_line'][-1] + ' . ' + '\n'
                if 'isUse_file_line' in result_dict[key]:
                    ans += 'Used in file : '
                    for val in result_dict[key]['isUse_file_line'][:-1]:
                        ans += val + ' , ' + '\n'
                    ans += result_dict[key]['isUse_file_line'][-1] + ' . ' + '\n'
                if 'is_a' in result_dict[key]:
                    count = 0
                    ans += 'Identifier type : '
                    for val in result_dict[key]['is_a'][:-1]:
                        ans += val + ' , '
                    ans += result_dict[key]['is_a'][-1] + ' . '
                    ans += '\n'
                if 'is_array' in result_dict[key]:
                    ans += 'Is Array : ' + result_dict[key]['is_array'][0] + '\n'
                if 'is_pointer' in result_dict[key]:
                    ans += 'Is Pointer : ' + result_dict[key]['is_pointer'][0] + '\n'
                if 'is_subclass_of' in result_dict[key]:
                    for val in result_dict[key]['is_subclass_of']:
                        ans += 'Is Subclass Of : ' + val + '\n'
                if 'is_friend_of' in result_dict[key]:
                    for val in result_dict[key]['is_friend_of']:
                        ans += 'Is Friend Of : ' + val + '\n'
                if 'has_id' in result_dict[key]:
                    ans += 'ID : ' + result_dict[key]['has_id'][0] + '\n'
                if 'multiple_inheritance' in result_dict[key]:
                    ans += 'Multiple Inheritance : ' + result_dict[key]['multiple_inheritance'][0] + '\n'

                ans += '\n'

        return ans

    #this is a template function for only name tokens
    def template_name_token(self,word_store,graph):

        ans = ''
        result_dict = defaultdict(dict)

        query = """
            PREFIX prop: <http://smartKT/ns/properties#>
            PREFIX symbol: <http://smartKT/ns/symbol#>

            SELECT DISTINCT ?id ?pred ?obj
            WHERE
            {
                {
                    ?id prop:name_token "%s";
                        prop:is_defined_file "%s";
                        ?pred ?obj.
                    FILTER (?pred IN (prop:storage_class, prop:is_defined_file, prop:type, prop:spelling, prop:is_a, prop:is_array, prop:array_size, prop:is_pointer, prop:is_subclass_of, prop:is_friend_of) ) .
                }
                UNION
                {
                    SELECT DISTINCT ?id ?pred ?obj
                    WHERE
                    {
                        ?id prop:name_token "%s";
                            prop:is_called_file "%s";
                            ?pred ?obj.
                        FILTER (?pred IN (prop:storage_class, prop:is_defined_file, prop:type, prop:spelling, prop:is_a, prop:is_array, prop:array_size, prop:is_pointer, prop:is_subclass_of, prop:is_friend_of) ) .
                    }
                }
                UNION
                {
                    SELECT DISTINCT ?id ?pred ?obj
                    WHERE
                    {
                        ?id prop:name_token "%s";
                            prop:is_extern_file "%s";
                            ?pred ?obj.
                        FILTER (?pred IN (prop:storage_class, prop:is_defined_file, prop:type, prop:spelling, prop:is_a, prop:is_array, prop:array_size, prop:is_pointer, prop:is_subclass_of, prop:is_friend_of) ) .
                    }
                }
            }
            """

        for ind,matched_tokens in enumerate(word_store['name_token']):
            print(matched_tokens[1])
            firstFile = self.tf_idf_name_tokens[matched_tokens[1]][0][0]
            # secondFile = self.tf_idf_name_tokens[matched_tokens[1]][1][0]
            # print(firstFile,secondFile)
            queryFirst = query % (matched_tokens[1],firstFile,matched_tokens[1],firstFile,matched_tokens[1],firstFile)
            # querySecond = query % (matched_tokens[1],secondFile,matched_tokens[1],secondFile,matched_tokens[1],secondFile)
            print(queryFirst)
            start_time = time.time()
            resultFirst = graph.query(queryFirst)
            # resultSecond = graph.query(querySecond)
            end_time = time.time()
            print("Time taken to process query",+end_time-start_time)

            for row in resultFirst:
                curr_id = row['id'].split('#')[1]
                result_dict[curr_id][str(row['pred'].split('#')[1])] = str(row['obj'])

            for key in result_dict:
                for attr in result_dict[key]:
                    ans += attr + ' : ' + result_dict[key][attr] + '\n'
                ans += '\n'

        return ans

    #where is the xy_test defined / where is the xy_test defined and it's storage class (1 symbol and multiple attributes since for multiple symbols we will have to do grouping)
    def template_attr_symbol(self,word_store,graph):

        ans = ''
        no_of_attributes = len(word_store['static_attribute'])
        result_set = defaultdict(set)

        query_part_1 = """
            PREFIX prop: <http://smartKT/ns/properties#>
            PREFIX symbol: <http://smartKT/ns/symbol#>

            """

        query_part_2 = "SELECT DISTINCT"

        for i in range(no_of_attributes):
            query_part_2 = query_part_2 + ' ?obj' + str(i+1)

        query_part_3 = """
                    WHERE
                    {
                        ?id prop:spelling "%s";
                    """

        query_part_4 = ''
        count = 0
        for i in range(no_of_attributes-1):
            count += 1
            query_part_4 = query_part_4 + 'prop:%s' + ' ?obj' + str(count) + ';' + '\n'

        query_part_4 = query_part_4 + 'prop:%s' + ' ?obj' + str(count+1) + '.' + '\n' + '}'

        all_attr_list = list()
        all_arguments = list()

        symbol_name = word_store['symbol'][0][1]

        for matched_attr in word_store['static_attribute']:
            attr_word = matched_attr[0]
            all_attr_list.append(list(self.all_store['static_attribute'][attr_word]))

        print(all_attr_list)

        if no_of_attributes == 1:
            for attr_ in all_attr_list:
                for attr_val in attr_:
                    element = (symbol_name,attr_val)
                    all_arguments.append(element)

        else:
            for element in itertools.product(*all_attr_list):   #we did this if a given word matches with multiple static attributes so considering all combinations. ((read-[isRead_file_line,READCOUNT]))
                element = list(element)
                element = [symbol_name] + element
                element = tuple(element)
                all_arguments.append(element)

        for arguments in all_arguments:
            query = query_part_1 + query_part_2 + query_part_3 + query_part_4
            print(query)
            print(arguments)
            query = query % arguments
            print(query)
            start_time = time.time()
            result = graph.query(query)
            end_time = time.time()
            print("Time taken to process query",+end_time-start_time)

            for ind1,row in enumerate(result):
                for ind2 in range(no_of_attributes):
                    if row['obj'+str(ind2+1)] not in result_set[ind2]:
                        result_set[ind2].add(row['obj'+str(ind2+1)])

        result_set = OrderedDict(sorted(result_set.items()))

        for ind,key in enumerate(result_set):
            attr_word = word_store['static_attribute'][ind][0]
            ans += 'Corresponding to the attribute : ' + attr_word + '\n'
            for res in result_set[key]:
                ans += res
                ans += '\n'

        print(ans)

        return ans

    #where is the variable xy_test defined / where is the variable xy_test defined and it's storage class (variable and class of storage class both are common words)
    def template_attr_common_symbol(self,word_store,graph):

        ans = ''
        no_of_attributes = len(word_store['static_attribute'])
        result_set = defaultdict(set)

        query_part_1 = """
            PREFIX prop: <http://smartKT/ns/properties#>
            PREFIX symbol: <http://smartKT/ns/symbol#>

            """

        query_part_2 = "SELECT DISTINCT "

        for i in range(no_of_attributes):
            query_part_2 = query_part_2 + ' ?obj' + str(i+1)

        query_part_3 = """
                    WHERE
                    {
                        ?id prop:spelling "%s";
                    """

        query_part_4 = ''

        all_attr_list = list()
        all_arguments = list()

        symbol_name = word_store['symbol'][0][1]

        for matched_attr in word_store['static_attribute']:
            attr_word = matched_attr[0]
            all_attr_list.append(list(self.all_store['static_attribute'][attr_word]))

        print(all_attr_list)

        for i in range(no_of_attributes):
            query_part_4 = query_part_4 + 'prop:%s' + ' ?obj' + str(i+1) + ';' + '\n'

        if no_of_attributes == 1:
            for attr_ in all_attr_list:
                for attr_val in attr_:
                    element = (symbol_name,attr_val)
                    all_arguments.append(element)

        else:
            for element in itertools.product(*all_attr_list):
                element = list(element)
                element = [symbol_name] + element
                element = tuple(element)
                all_arguments.append(element)

        for arguments in all_arguments:

            for matched_word in word_store['common_word']:
                word = matched_word[0]
                tag_list = self.all_store['common_word'][word]

                for tag in tag_list:
                    query_part_5 = 'prop:is_a' + ' ' + '"' + str(tag) + '"' + '.' + '\n' + '}'

                    query = query_part_1 + query_part_2 + query_part_3 + query_part_4 + query_part_5
                    print(arguments)
                    query = query % arguments
                    print(query)
                    start_time = time.time()
                    result = graph.query(query)
                    end_time = time.time()
                    print("Time taken to process query",+end_time-start_time)

                    if len(result)!=0:
                        for row in result:
                            for ind2 in range(no_of_attributes):
                                if row['obj'+str(ind2+1)] not in result_set[ind2]:
                                    result_set[ind2].add(row['obj'+str(ind2+1)])

        result_set = OrderedDict(sorted(result_set.items()))

        for ind,key in enumerate(result_set):
            attr_word = word_store['static_attribute'][ind][0]
            ans += 'Corresponding to the attribute : ' + attr_word + '\n'
            for res in result_set[key]:
                ans += res
                ans += '\n'

        print(ans)

        return ans

    #list all the variables in file png.c / list all the variables in file png.c and png.h (1 common word and multiple symbols then we assume attribute is "is_defined_file")
    def template_common_file(self,word_store,graph):

        ans = ''
        result_set = set()
        result_dict = defaultdict(dict)

        query_part_1 = """
            PREFIX prop: <http://smartKT/ns/properties#>
            PREFIX symbol: <http://smartKT/ns/symbol#>

            """

        query_part_2 = "SELECT DISTINCT ?id ?pred ?obj"

        query_part_3 = """
                    WHERE
                    {
                        ?id ?pred ?obj ;
                    """

        query_part_6 = """
            FILTER (?pred IN (prop:storage_class, prop:is_defined_file, prop:type, prop:spelling, prop:is_a, prop:is_array, prop:array_size, prop:is_pointer, prop:is_subclass_of, prop:is_friend_of) ) .
            }
            """

        for ind,matched_symbol in enumerate(word_store['fil']):
            file_name = matched_symbol[1]
            query_part_4 = 'prop:is_defined_file' + ' ' + '"' + file_name + '"' + ';' + '\n'

            for matched_word in word_store['common_word']:
                word = matched_word[0]
                tag_list = self.all_store['common_word'][word]

                for tag in tag_list:
                    query_part_5 = 'prop:is_a' + ' ' + '"' + str(tag) + '"' + '.'

                    query = query_part_1 + query_part_2 + query_part_3 + query_part_4 + query_part_5 + query_part_6
                    print(query)

                    start_time = time.time()
                    result = graph.query(query)
                    end_time = time.time()
                    print("Time taken to process query",+end_time-start_time)

                    prev_id = None
                    ans_temp = ''

                    for row in result:
                        curr_id = row['id'].split('#')[1]
                        result_dict[curr_id][str(row['pred'].split('#')[1])] = str(row['obj'])


        for key in result_dict:
            if 'spelling' in result_dict[key]:
                ans += 'Identifier name : ' + result_dict[key]['spelling'] + '\n'
            if 'storage_class' in result_dict[key]:
               ans += 'Storage class : ' + result_dict[key]['storage_class'] + '\n'
            if 'type' in result_dict[key]:
                ans += 'Datatype : ' + result_dict[key]['type'] + '\n'
            if 'is_defined_file' in result_dict[key]:
                ans += 'Definition file : ' + result_dict[key]['is_defined_file'] + '\n'
            if 'is_a' in result_dict[key]:
                ans += 'Identifier type : ' + result_dict[key]['is_a'] + '\n\n'

        return ans

    #(List all the variables in function png_do_read_invert_alpha / List all the functions with row as a variable -- variables and function are two common words) / List all the functions with row as a variable and all functions with i as a variable (intersection won't work)
    def template_common_symbol(self,word_store,graph):

        ans = ''

        query_part_1 = """
            PREFIX prop: <http://smartKT/ns/properties#>
            PREFIX symbol: <http://smartKT/ns/symbol#>

            """

        query_part_2 = "SELECT DISTINCT ?name"

        query_part_3 = """
                    WHERE
                    {
                        ?var prop:spelling "%s";
                            prop:lex_parent_id ?id.
                        ?id prop:spelling ?name;
                    """

        query_part_3_1 = """
                    WHERE
                    {
                        ?id prop:spelling "%s".
                        ?var prop:lex_parent_id ?id;
                            prop:spelling ?name;
                    """

        if len(word_store['symbol']) > 1:
            ans = self.template_symbol(word_store,graph)
            return ans

        for matched_symbol in word_store['symbol']:
            symbol_name = matched_symbol[1]

            for matched_word in word_store['common_word']:
                word = matched_word[0]
                print(word)
                tag_list = self.all_store['common_word'][word]

                for tag in tag_list:
                    query_part_4 = 'prop:is_a' + ' ' + '"' + str(tag) + '"' + '.' + '\n'
                    query_part_5 = 'FILTER strStarts(str(?id),str(symbol:)).' + '\n'
                    query_part_6 = 'FILTER strStarts(str(?var),str(symbol:)).' + '\n' + '}'

                    query1 = query_part_1 + query_part_2 + query_part_3 + query_part_4 + query_part_5 + query_part_6
                    query2 = query_part_1 + query_part_2 + query_part_3_1 + query_part_4 + query_part_5 + query_part_6

                    query1 = query1 % symbol_name
                    query2 = query2 % symbol_name

                    print(query2)

                    start_time = time.time()
                    result1 = graph.query(query1)
                    result2 = graph.query(query2)
                    end_time = time.time()
                    print("Time taken to process query",+end_time-start_time)

                    for row in result1:
                        ans += row['name'] + '\n'

                    for row in result2:
                        ans += row['name'] + '\n'

                    print(ans)
        return ans

    #list all the functions / list all the variables / list all the functions in file __
    def template_common_word(self,word_store,graph):

        ans = ''
        file_name = ''
        result_set = set()

        if 'fil' in word_store:
            for matched_file in word_store['fil']:
                file_name = matched_file[1]

        query_part_1 = """
            PREFIX prop: <http://smartKT/ns/properties#>
            PREFIX symbol: <http://smartKT/ns/symbol#>

            """

        query_part_2 = "SELECT DISTINCT ?name"

        query_part_3 = """
                    WHERE
                    {
                        ?id prop:spelling ?name;
                    """

        query_part_4 = 'prop:is_defined_file' + ' ' + '"' + file_name + '"' + ';' + '\n'

        for matched_word in word_store['common_word']:
            word = matched_word[0]
            tag_list = self.all_store['common_word'][word]

            for tag in tag_list:
                query_part_5 = 'prop:is_a' + ' ' + '"' + str(tag) + '"' + '.' + '\n' + '}'

                if file_name:
                    query = query_part_1 + query_part_2 + query_part_3 + query_part_4 + query_part_5
                else:
                    query = query_part_1 + query_part_2 + query_part_3 + query_part_5
                print(query)

                start_time = time.time()
                result = graph.query(query)
                end_time = time.time()
                print("Time taken to process query",+end_time-start_time)

                for row in result:
                    result_set.add(row['name'])

        for res in result_set:
            ans += res
            ans += '\n'
        print(ans)

        return ans

    #list all the extern functions / list all the static variables / list all the static variables with return type int
    def template_value_common(self,word_store,graph):

        ans = ''
        stmt1 = ''
        stmt2 = ''
        #all_store['values']['int'] = set(['type','return_type'])

        query_part_1 = """
            PREFIX prop: <http://smartKT/ns/properties#>
            PREFIX symbol: <http://smartKT/ns/symbol#>

            """

        query_part_2 = "SELECT DISTINCT ?id ?pred ?obj"

        query_part_3 = """
                WHERE
                {
                    ?id ?pred ?obj ;
            """

        query_part_6 = """
            FILTER (?pred IN (prop:storage_class, prop:is_defined_file, prop:type, prop:spelling, prop:is_a, prop:is_array, prop:array_size, prop:is_pointer, prop:is_subclass_of, prop:is_friend_of) ) .
            }
            """

        query_part_4_f = ''

        query_in = query_part_1 + query_part_2 + query_part_3

        for matched_val in word_store['values']:
            val = matched_val[0]
            attr = list(self.all_store['values'][val])[0]
            if attr == 'type' or attr == 'return_type':
                stmt1 = 'prop:type' + ' ' + '"' + val + '"' + ';' + '\n'
                stmt2 = 'prop:return_type' + ' ' + '"' + val + '"' + ';' + '\n'
            else:
                query_part_4 = 'prop:%s' % attr + ' ' + '"' + val + '"' + ';' + '\n'
                query_part_4_f = query_part_4_f + query_part_4

        for matched_word in word_store['common_word']:
            word = matched_word[0]
            tag_list = self.all_store['common_word'][word]

            for tag in tag_list:
                query_part_5 = 'prop:is_a' + ' ' + '"' + str(tag) + '"' + '.'

                query = query_in + stmt1 + query_part_4_f + query_part_5 + query_part_6
                print(query)

                start_time = time.time()
                result = graph.query(query)
                end_time = time.time()
                print("Time taken to process query",+end_time-start_time)

                prev_id = None
                ans_temp = ''

                if len(result)!=0:

                    for i,row in enumerate(result):
                        curr_id = row['id'].split('#')[1]
                        if curr_id == prev_id:
                            ans_temp = ans_temp + row['pred'].split('#')[1] + ' ' + row['obj']+'\n'
                        else:
                            ans += ans_temp + '\n'
                            ans_temp = 'ID is: ' + curr_id + '\n'
                            ans_temp = ans_temp + row['pred'].split('#')[1] + ' ' + row['obj']+'\n'
                            prev_id = curr_id

                    ans += ans_temp + '\n'

                else:
                    query = query_in + stmt2 + query_part_4_f + query_part_5 + query_part_6
                    print(query)

                    start_time = time.time()
                    result = graph.query(query)
                    end_time = time.time()
                    print("Time taken to process query",+end_time-start_time)

                    for i,row in enumerate(result):
                        curr_id = row['id'].split('#')[1]
                        if curr_id == prev_id:
                            ans_temp = ans_temp + row['pred'].split('#')[1] + ' ' + row['obj']+'\n'
                        else:
                            ans += ans_temp + '\n'
                            ans_temp = 'ID is: ' + curr_id + '\n'
                            ans_temp = ans_temp + row['pred'].split('#')[1] + ' ' + row['obj']+'\n'
                            prev_id = curr_id

                    ans += ans_temp + '\n'

        return ans

    #list the variables with return type int in function ___
    def template_value_common_symbol(self,word_store,graph):

        ans = ''
        result_set = set()
        #all_store['values']['int'] = set(['type','return_type'])

        query_part_1 = """
            PREFIX prop: <http://smartKT/ns/properties#>
            PREFIX symbol: <http://smartKT/ns/symbol#>

            """

        query_part_2 = "SELECT DISTINCT ?name"

        query_part_3 = """
                WHERE
                {
                    ?id prop:spelling "%s".
                    ?var prop:lex_parent_id ?id;
                         prop:spelling ?name;
                """

        query_part_4_f = ''

        query_in = query_part_1 + query_part_2 + query_part_3

        for matched_symbol in word_store['symbol']:
            symbol_name = matched_symbol[1]

        for matched_val in word_store['values']:
            val = matched_val[0]
            attr = list(self.all_store['values'][val])[0]
            if attr == 'type' or attr == 'return_type':
                stmt1 = 'prop:type' + ' ' + '"' + val + '"' + ';' + '\n'
            else:
                query_part_4 = 'prop:%s' % attr + ' ' + '"' + val + '"' + ';' + '\n'
                query_part_4_f = query_part_4_f + query_part_4

        for matched_word in word_store['common_word']:
            word = matched_word[0]
            tag_list = self.all_store['common_word'][word]

            for tag in tag_list:
                query_part_5 = 'prop:is_a' + ' ' + '"' + str(tag) + '"' + '.' + '\n' + '}'

                query = query_in + stmt1 + query_part_4_f + query_part_5
                query = query % symbol_name
                print(query)

                start_time = time.time()
                result = graph.query(query)
                end_time = time.time()
                print("Time taken to process query",+end_time-start_time)

                for row in result:
                    result_set.add(row['name'])

        for res in result_set:
            ans += res
            ans += '\n'
        print(ans)

        return ans

    #List the functions with return type int in file png.c
    def template_value_common_file(self,word_store,graph):

        ans = ''
        stmt1 = ''
        stmt2 = ''
        result_set = set()
        #all_store['values']['int'] = set(['type','return_type'])

        query_part_1 = """
            PREFIX prop: <http://smartKT/ns/properties#>
            PREFIX symbol: <http://smartKT/ns/symbol#>

            """

        query_part_2 = "SELECT DISTINCT ?name"

        query_part_3 = """
                WHERE
                {
                    ?id prop:is_defined_file "%s";
                        prop:spelling ?name;
                """

        query_part_4_f = ''

        query_in = query_part_1 + query_part_2 + query_part_3

        for matched_symbol in word_store['fil']:
            symbol_name = matched_symbol[1]

        for matched_val in word_store['values']:
            val = matched_val[0]
            attr = list(self.all_store['values'][val])[0]
            if attr == 'type' or attr == 'return_type':
                stmt1 = 'prop:type' + ' ' + '"' + val + '"' + ';' + '\n'
            else:
                query_part_4 = 'prop:%s' % attr + ' ' + '"' + val + '"' + ';' + '\n'
                query_part_4_f = query_part_4_f + query_part_4

        for matched_word in word_store['common_word']:
            word = matched_word[0]
            tag_list = self.all_store['common_word'][word]

            for tag in tag_list:
                query_part_5 = 'prop:is_a' + ' ' + '"' + str(tag) + '"' + '.' + '\n' + '}'

                query = query_in + stmt1 + query_part_4_f + query_part_5
                query = query % symbol_name
                print(query)

                start_time = time.time()
                result = graph.query(query)
                end_time = time.time()
                print("Time taken to process query",+end_time-start_time)

                for row in result:
                    result_set.add(row['name'])

        for res in result_set:
            ans += res
            ans += '\n'
        print(ans)

        return ans

    #this is a template function for only comment tokens
    def template_comment_token(self,word_store,graph):

        ans = ''
        result_comment_all = defaultdict(dict)
        result_comment_first = defaultdict(dict)
        result_name_all = defaultdict(dict)
        result_name_first = defaultdict(dict)

        query = """
            PREFIX prop: <http://smartKT/ns/properties#>
            PREFIX symbol: <http://smartKT/ns/symbol#>

            SELECT DISTINCT ?id ?pred ?obj
            WHERE
            {
                {
                    ?id prop:comment_token "%s" ;
                        ?pred ?obj .
                    FILTER strStarts(str(?id),str(symbol:)) .
                    FILTER (?pred IN (prop:storage_class, prop:isDef_file_line, prop:type, prop:spelling, prop:is_a) ) .
                }

            }
            """

        query_alt = """
            PREFIX prop: <http://smartKT/ns/properties#>
            PREFIX symbol: <http://smartKT/ns/symbol#>

            SELECT DISTINCT ?id ?pred ?obj
            WHERE
            {
                {
                    ?id prop:name_token "%s";
                        prop:is_defined_file "%s";
                        ?pred ?obj.
                    FILTER (?pred IN (prop:storage_class, prop:isDef_file_line, prop:type, prop:spelling, prop:is_a) ) .
                }
                UNION
                {
                    SELECT DISTINCT ?id ?pred ?obj
                    WHERE
                    {
                        ?id prop:name_token "%s";
                            prop:is_called_file "%s";
                            ?pred ?obj.
                        FILTER (?pred IN (prop:storage_class, prop:isDef_file_line, prop:type, prop:spelling, prop:is_a) ) .
                    }
                }
                UNION
                {
                    SELECT DISTINCT ?id ?pred ?obj
                    WHERE
                    {
                        ?id prop:name_token "%s";
                            prop:is_extern_file "%s";
                            ?pred ?obj.
                        FILTER (?pred IN (prop:storage_class, prop:isDef_file_line, prop:type, prop:spelling, prop:is_a) ) .
                    }
                }
            }

            """

        for ind,matched_tokens in enumerate(word_store['comment_token']):
            print(query)
            print(matched_tokens[1])
            queryFirst = query % (matched_tokens[1])
            # print(query)
            start_time = time.time()
            resultFirst = graph.query(queryFirst)
            end_time = time.time()
            # print("Time taken to process query",+end_time-start_time)

            for row in resultFirst:
                if ind < self.syntax_count:
                    curr_id = row['id'].split('#')[1]
                    if curr_id in result_comment_first:
                        result_comment_first[curr_id][str(row['pred'].split('#')[1])] = str(row['obj'])
                    else:
                        result_comment_first[curr_id][str(row['pred'].split('#')[1])] = str(row['obj'])
                        result_comment_first[curr_id]['match_name'] = matched_tokens[1]
                        result_comment_first[curr_id]['match_location'] = 'comments'
                else:
                    curr_id = row['id'].split('#')[1]
                    if curr_id in result_comment_all:
                        result_comment_all[curr_id][str(row['pred'].split('#')[1])] = str(row['obj'])
                    else:
                        if curr_id not in result_comment_first:
                            result_comment_all[curr_id][str(row['pred'].split('#')[1])] = str(row['obj'])
                            result_comment_all[curr_id]['match_name'] = matched_tokens[1]
                            result_comment_all[curr_id]['match_location'] = 'comments'


        if self.conflict_flag:
            for ind,matched_tokens in enumerate(self.conflict_words):

                firstFile = self.tf_idf_name_tokens[matched_tokens[1]][0][0]
                queryFirst = query_alt % (matched_tokens[1],firstFile,matched_tokens[1],firstFile,matched_tokens[1],firstFile)
                # print(queryFirst)
                start_time = time.time()
                resultFirst = graph.query(queryFirst)
                end_time = time.time()
                # print("Time taken to process query",+end_time-start_time)

                for row in resultFirst:
                    if ind==0:
                        curr_id = row['id'].split('#')[1]
                        if curr_id in result_name_first:
                            result_name_first[curr_id][str(row['pred'].split('#')[1])] = str(row['obj'])
                        else:
                            if curr_id not in result_comment_first and result_comment_all:
                                result_name_first[curr_id][str(row['pred'].split('#')[1])] = str(row['obj'])
                                result_name_first[curr_id]['match_name'] = matched_tokens[1]
                                result_name_first[curr_id]['match_location'] = 'identifiers'
                    else:
                        curr_id = row['id'].split('#')[1]
                        if curr_id in result_name_all:
                            result_name_all[curr_id][str(row['pred'].split('#')[1])] = str(row['obj'])
                        else:
                            if curr_id not in result_name_first and result_comment_first and result_comment_all:
                                result_name_all[curr_id][str(row['pred'].split('#')[1])] = str(row['obj'])
                                result_name_all[curr_id]['match_name'] = matched_tokens[1]
                                result_name_all[curr_id]['match_location'] = 'identifiers'

        #predicates are : spelling, type, is_a, def_file_line, match_location

        # ans += '\n' + 'Syntactical matches in code base :' + '\n' + '\n'

        if result_comment_first:
            for key in result_comment_first:
                if 'spelling' in result_comment_first[key]:
                    ans += 'Identifier name : ' + result_comment_first[key]['spelling'] + '\n'
                if 'storage_class' in result_comment_first[key]:
                   ans += 'Storage class : ' + result_comment_first[key]['storage_class'] + '\n'
                if 'type' in result_comment_first[key]:
                    ans += 'Datatype : ' + result_comment_first[key]['type'] + '\n'
                if 'is_defined_file' in result_comment_first[key]:
                    ans += 'Definition file : ' + result_comment_first[key]['is_defined_file'] + '\n'
                if 'is_a' in result_comment_first[key]:
                    ans += 'Identifier type : ' + result_comment_first[key]['is_a'] + '\n'
                ans += 'Match name : ' + result_comment_first[key]['match_name'] + '\n'
                ans += 'Match location : ' + result_comment_first[key]['match_location'] + '\n\n'


        if result_name_first:
            for key in result_name_first:
                if 'spelling' in result_name_first[key]:
                    ans += 'Identifier name : ' + result_name_first[key]['spelling'] + '\n'
                if 'storage_class' in result_name_first[key]:
                   ans += 'Storage class : ' + result_name_first[key]['storage_class'] + '\n'
                if 'type' in result_name_first[key]:
                    ans += 'Datatype : ' + result_name_first[key]['type'] + '\n'
                if 'is_defined_file' in result_name_first[key]:
                    ans += 'Definition file : ' + result_name_first[key]['is_defined_file'] + '\n'
                if 'is_a' in result_name_first[key]:
                    ans += 'Identifier type : ' + result_name_first[key]['is_a'] + '\n'
                ans += 'Match name : ' + result_name_first[key]['match_name'] + '\n'
                ans += 'Match location : ' + result_name_first[key]['match_location'] + '\n\n'

        ans += '\n'

        # ans += 'Semantical matches in code base :' + '\n\n'

        if result_comment_all:
            for key in result_comment_all:
                if 'spelling' in result_comment_all[key]:
                    ans += 'Identifier name : ' + result_comment_all[key]['spelling'] + '\n'
                if 'storage_class' in result_comment_all[key]:
                   ans += 'Storage class : ' + result_comment_all[key]['storage_class'] + '\n'
                if 'type' in result_comment_all[key]:
                    ans += 'Datatype : ' + result_comment_all[key]['type'] + '\n'
                if 'is_defined_file' in result_comment_all[key]:
                    ans += 'Definition file : ' + result_comment_all[key]['is_defined_file'] + '\n'
                if 'is_a' in result_comment_all[key]:
                    ans += 'Identifier type : ' + result_comment_all[key]['is_a'] + '\n'
                ans += 'Match name : ' + result_comment_all[key]['match_name'] + '\n'
                ans += 'Match location : ' + result_comment_all[key]['match_location'] + '\n\n'


        if result_name_all:
            for key in result_name_all:
                if 'spelling' in result_name_all[key]:
                    ans += 'Identifier name : ' + result_name_all[key]['spelling'] + '\n'
                if 'storage_class' in result_name_all[key]:
                   ans += 'Storage class : ' + result_name_all[key]['storage_class'] + '\n'
                if 'type' in result_name_all[key]:
                    ans += 'Datatype : ' + result_name_all[key]['type'] + '\n'
                if 'is_defined_file' in result_name_all[key]:
                    ans += 'Definition file : ' + result_name_all[key]['is_defined_file'] + '\n'
                if 'is_a' in result_name_all[key]:
                    ans += 'Identifier type : ' + result_name_all[key]['is_a'] + '\n'
                ans += 'Match name : ' + result_name_all[key]['match_name'] + '\n'
                ans += 'Match location : ' + result_name_all[key]['match_location'] + '\n\n'

        return ans

    # List all the sort functions
    def template_comment_common(self,word_store,graph):

        ans = ''
        file_name = ''
        result_comment_all = defaultdict(dict)
        result_comment_first = defaultdict(dict)
        result_name_all = defaultdict(dict)
        result_name_first = defaultdict(dict)
        all_attr_list = list()
        no_of_attributes = len(word_store['static_attribute'])

        if 'fil' in word_store:
            for matched_file in word_store['fil']:
                file_name = matched_file[1]

        query_alt = """
            PREFIX prop: <http://smartKT/ns/properties#>
            PREFIX symbol: <http://smartKT/ns/symbol#>

            SELECT DISTINCT ?id ?pred ?obj
            WHERE
            {
                {
                    ?id prop:name_token "%s";
                        prop:is_defined_file "%s";
                        ?pred ?obj.
                    FILTER (?pred IN (prop:storage_class, prop:isDef_file_line, prop:type, prop:spelling, prop:is_a) ) .
                }
                UNION
                {
                    SELECT DISTINCT ?id ?pred ?obj
                    WHERE
                    {
                        ?id prop:name_token "%s";
                            prop:is_called_file "%s";
                            ?pred ?obj.
                        FILTER (?pred IN (prop:storage_class, prop:isDef_file_line, prop:type, prop:spelling, prop:is_a) ) .
                    }
                }
                UNION
                {
                    SELECT DISTINCT ?id ?pred ?obj
                    WHERE
                    {
                        ?id prop:name_token "%s";
                            prop:is_extern_file "%s";
                            ?pred ?obj.
                        FILTER (?pred IN (prop:storage_class, prop:isDef_file_line, prop:type, prop:spelling, prop:is_a) ) .
                    }
                }
            }

            """

        query_part_1 = """
            PREFIX prop: <http://smartKT/ns/properties#>
            PREFIX symbol: <http://smartKT/ns/symbol#>

            SELECT DISTINCT ?id ?pred ?obj
            WHERE
            {
                ?id prop:comment_token "%s" ;
                    ?pred ?obj ;
            """

        if no_of_attributes != 0:
            count = 0
            for i in range(no_of_attributes-1):
                count += 1
                query_part_1 = query_part_1 + 'prop:%s' + ' ?obj' + str(count) + ';' + '\n'

            query_part_1 = query_part_1 + 'prop:%s' + ' ?obj' + str(count+1) + ';' + '\n'

            for matched_attr in word_store['static_attribute']:
                attr_word = matched_attr[0]
                all_attr_list.append(list(self.all_store['static_attribute'][attr_word])[0])


        query_part_2 = """
                prop:is_defined_file "%s" ;
        """

        query_part_2 = query_part_2 % file_name

        query_part_4 = """
            FILTER (?pred IN (prop:storage_class, prop:isDef_file_line, prop:isWritten_file_line, prop:isRead_file_line, prop:type, prop:spelling, prop:is_a) ) .
            FILTER strStarts(str(?id),str(symbol:)) .
            }
            """

        for ind,matched_tokens in enumerate(word_store['comment_token']):

            if no_of_attributes!=0:
                arguments = [matched_tokens[1]] + all_attr_list
                arguments = tuple(arguments)
            else:
                arguments = (matched_tokens[1])

            if ind==0:
                print('-------------------------first comment token----------------')
                print(matched_tokens)

            for matched_word in word_store['common_word']:
                word = matched_word[0]
                tag_list = self.all_store['common_word'][word]

                for tag in tag_list:
                    query_part_3 = 'prop:is_a' + ' ' + '"' + str(tag) + '"' + '.' + '\n'

                    if file_name:
                        query = query_part_1 + query_part_2 + query_part_3 + query_part_4
                    else:
                        query = query_part_1 + query_part_3 + query_part_4

                    query = query % arguments
                    print(query)
                    start_time = time.time()
                    resultFirst = graph.query(query)
                    end_time = time.time()
                    # print("Time taken to process query",+end_time-start_time)

                    for row in resultFirst:
                        if ind < self.syntax_count:
                            print('syntactical match :' +matched_tokens[1])
                            curr_id = row['id'].split('#')[1]
                            if curr_id in result_comment_first:
                                result_comment_first[curr_id][str(row['pred'].split('#')[1])] = str(row['obj'])
                            else:
                                result_comment_first[curr_id][str(row['pred'].split('#')[1])] = str(row['obj'])
                                result_comment_first[curr_id]['match_name'] = matched_tokens[1]
                                result_comment_first[curr_id]['match_location'] = 'comments'
                        else:
                            print('semantical match :' +matched_tokens[1])
                            curr_id = row['id'].split('#')[1]
                            if curr_id in result_comment_all:
                                result_comment_all[curr_id][str(row['pred'].split('#')[1])] = str(row['obj'])
                            else:
                                if curr_id not in result_comment_first:
                                    result_comment_all[curr_id][str(row['pred'].split('#')[1])] = str(row['obj'])
                                    result_comment_all[curr_id]['match_name'] = matched_tokens[1]
                                    result_comment_all[curr_id]['match_location'] = 'comments'


        if self.conflict_flag:
            for ind,matched_tokens in enumerate(self.conflict_words):

                firstFile = self.tf_idf_name_tokens[matched_tokens[1]][0][0]
                queryFirst = query_alt % (matched_tokens[1],firstFile,matched_tokens[1],firstFile,matched_tokens[1],firstFile)
                # print(queryFirst)
                start_time = time.time()
                resultFirst = graph.query(queryFirst)
                end_time = time.time()
                # print("Time taken to process query",+end_time-start_time)

                for row in resultFirst:
                    if ind == 0:
                        curr_id = row['id'].split('#')[1]
                        if curr_id in result_name_first:
                            result_name_first[curr_id][str(row['pred'].split('#')[1])] = str(row['obj'])
                        else:
                            if curr_id not in result_comment_first and curr_id not in result_comment_all:
                                result_name_first[curr_id][str(row['pred'].split('#')[1])] = str(row['obj'])
                                result_name_first[curr_id]['match_name'] = matched_tokens[1]
                                result_name_first[curr_id]['match_location'] = 'identifiers'
                    else:
                        curr_id = row['id'].split('#')[1]
                        if curr_id in result_name_all:
                            result_name_all[curr_id][str(row['pred'].split('#')[1])] = str(row['obj'])
                        else:
                            if curr_id not in result_name_first and curr_id not in result_comment_first and curr_id not in result_comment_all:
                                result_name_all[curr_id][str(row['pred'].split('#')[1])] = str(row['obj'])
                                result_name_all[curr_id]['match_name'] = matched_tokens[1]
                                result_name_all[curr_id]['match_location'] = 'identifiers'

        #predicates are : spelling, type, is_a, def_file_line, match_location

        # ans += '\n' + 'Syntactical matches in code base :' + '\n' + '\n'

        if result_comment_first:
            for key in result_comment_first:
                if 'spelling' in result_comment_first[key]:
                    ans += 'Identifier name : ' + result_comment_first[key]['spelling'] + '\n'
                if 'storage_class' in result_comment_first[key]:
                   ans += 'Storage class : ' + result_comment_first[key]['storage_class'] + '\n'
                if 'type' in result_comment_first[key]:
                    ans += 'Datatype : ' + result_comment_first[key]['type'] + '\n'
                if 'isDef_file_line' in result_comment_first[key]:
                    ans += 'Definition file : ' + result_comment_first[key]['isDef_file_line'] + '\n'
                if 'isWritten_file_line' in result_comment_first[key]:
                    ans += 'Written in file : ' + result_comment_first[key]['isWritten_file_line'] + '\n'
                if 'isRead_file_line' in result_comment_first[key]:
                    ans += 'Read in file : ' + result_comment_first[key]['isRead_file_line'] + '\n'
                if 'is_a' in result_comment_first[key]:
                    ans += 'Identifier type : ' + result_comment_first[key]['is_a'] + '\n'
                ans += 'Match name : ' + result_comment_first[key]['match_name'] + '\n'
                ans += 'Match location : ' + result_comment_first[key]['match_location'] + '\n\n'


        if result_name_first:
            for key in result_name_first:
                if 'spelling' in result_name_first[key]:
                    ans += 'Identifier name : ' + result_name_first[key]['spelling'] + '\n'
                if 'storage_class' in result_name_first[key]:
                   ans += 'Storage class : ' + result_name_first[key]['storage_class'] + '\n'
                if 'type' in result_name_first[key]:
                    ans += 'Datatype : ' + result_name_first[key]['type'] + '\n'
                if 'isDef_file_line' in result_name_first[key]:
                    ans += 'Definition file : ' + result_name_first[key]['isDef_file_line'] + '\n'
                if 'is_a' in result_name_first[key]:
                    ans += 'Identifier type : ' + result_name_first[key]['is_a'] + '\n'
                ans += 'Match name : ' + result_name_first[key]['match_name'] + '\n'
                ans += 'Match location : ' + result_name_first[key]['match_location'] + '\n\n'

        ans += '\n'

        # ans += 'Semantical matches in code base :' + '\n\n'

        if result_comment_all:
            for key in result_comment_all:
                if 'spelling' in result_comment_all[key]:
                    ans += 'Identifier name : ' + result_comment_all[key]['spelling'] + '\n'
                if 'storage_class' in result_comment_all[key]:
                   ans += 'Storage class : ' + result_comment_all[key]['storage_class'] + '\n'
                if 'type' in result_comment_all[key]:
                    ans += 'Datatype : ' + result_comment_all[key]['type'] + '\n'
                if 'isDef_file_line' in result_comment_all[key]:
                    ans += 'Definition file : ' + result_comment_all[key]['isDef_file_line'] + '\n'
                if 'isWritten_file_line' in result_comment_first[key]:
                    ans += 'Written in file : ' + result_comment_first[key]['isWritten_file_line'] + '\n'
                if 'isRead_file_line' in result_comment_first[key]:
                    ans += 'Read in file : ' + result_comment_first[key]['isRead_file_line'] + '\n'
                if 'is_a' in result_comment_all[key]:
                    ans += 'Identifier type : ' + result_comment_all[key]['is_a'] + '\n'
                ans += 'Match name : ' + result_comment_all[key]['match_name'] + '\n'
                ans += 'Match location : ' + result_comment_all[key]['match_location'] + '\n\n'


        if result_name_all:
            for key in result_name_all:
                if 'spelling' in result_name_all[key]:
                    ans += 'Identifier name : ' + result_name_all[key]['spelling'] + '\n'
                if 'storage_class' in result_name_all[key]:
                   ans += 'Storage class : ' + result_name_all[key]['storage_class'] + '\n'
                if 'type' in result_name_all[key]:
                    ans += 'Datatype : ' + result_name_all[key]['type'] + '\n'
                if 'isDef_file_line' in result_name_all[key]:
                    ans += 'Definition file : ' + result_name_all[key]['isDef_file_line'] + '\n'
                if 'is_a' in result_name_all[key]:
                    ans += 'Identifier type : ' + result_name_all[key]['is_a'] + '\n'
                ans += 'Match name : ' + result_name_all[key]['match_name'] + '\n'
                ans += 'Match location : ' + result_name_all[key]['match_location'] + '\n\n'

        return ans

    # which member variables of class A is involved in sorting algo / which variables of function A is involved in sorting algo
    def template_common_symbol_comment(self,word_store,graph):

        ans = ''

        query_part_1 = """
            PREFIX prop: <http://smartKT/ns/properties#>
            PREFIX symbol: <http://smartKT/ns/symbol#>

            """

        query_part_2 = "SELECT DISTINCT ?id ?pred ?obj"

        query_part_3 = """
                    WHERE
                    {
                        ?sym prop:lex_parent_id ?id;
                             prop:comment_token "%s";
                            ?pred ?obj.
                        ?id prop:spelling "%s" ;
                    """

        query_part_5 = """
            FILTER (?pred IN (prop:storage_class, prop:is_defined_file, prop:type, prop:spelling, prop:is_a) ) .
            FILTER strStarts(str(?sym),str(symbol:)) .
            }
            """

        for matched_symbol in word_store['symbol']:
            symbol_name = matched_symbol[1]
            break

        for ind,matched_token in enumerate(word_store['comment_token']):
            comment_token = matched_token[1]

            for matched_word in word_store['common_word']:
                word = matched_word[0]
                print(word)
                tag_list = self.all_store['common_word'][word]

                for tag in tag_list:
                    query_part_4 = 'prop:is_a' + ' ' + '"' + str(tag) + '"' + '.' + '\n'

                    query = query_part_1 + query_part_2 + query_part_3 + query_part_4 + query_part_5

                    query = query % (comment_token,symbol_name)

                    print(query)

                    start_time = time.time()
                    result = graph.query(query)
                    end_time = time.time()
                    print("Time taken to process query",+end_time-start_time)

                    prev_id = None
                    ans_temp = ''

                    for i,row in enumerate(result):
                        if i==0:
                            ans += '\n' + 'Results fetched for comment token ' + ':' + matched_tokens[1] + '\n'
                        curr_id = row['id'].split('#')[1]
                        if curr_id == prev_id:
                            ans_temp = ans_temp + row['pred'].split('#')[1] + ' ' + row['obj']+'\n'
                        else:
                            ans += ans_temp + '\n'
                            ans_temp = 'ID is: ' + curr_id + '\n'
                            ans_temp = ans_temp + row['pred'].split('#')[1] + ' ' + row['obj']+'\n'
                            prev_id = curr_id

                    if ans_temp:
                        ans += ans_temp + '\n'

        return ans

    #read write sequence of variables associated with globals
    def template_dynamic_attr_common_comment_token(self,word_store,graph):

        ans = ''
        rw_flag = False
        call_flag = False
        stat = False
        result = defaultdict(dict)
        result_static = defaultdict(dict)
        all_attr_list = list()
        no_of_attributes = len(word_store['static_attribute'])
        count = 0

        for matched_attr in word_store['dynamic_attribute']:
            if matched_attr[0] == "read-write" or matched_attr[0] == "read write" or matched_attr[0] == "read" or matched_attr[0] == "write":
                rw_flag = True
                break
            elif matched_attr[0] == "callee":
                call_flag = True
                break


        query_alt = """

            PREFIX prop: <http://smartKT/ns/properties#>
            PREFIX symbol: <http://smartKT/ns/symbol#>

            SELECT ?id ?pred ?obj
            WHERE
            {
                ?varId prop:comment_token "%s" ;
                       prop:spelling ?name .
                ?seq   prop:callee_name ?cname ;
                       prop:caller_name ?name .
                ?id    prop:spelling ?cname ;

        """

        if no_of_attributes!= 0:
            count = 0
            for i in range(no_of_attributes-1):
                count += 1
                query_alt = query_alt + 'prop:%s' + ' ?obj' + str(count) + ';' + '\n'

            query_alt = query_alt + 'prop:%s' + ' ?obj' + str(count+1) + ';' + '\n'

            for matched_attr in word_store['static_attribute']:
                attr_word = matched_attr[0]
                all_attr_list.append(list(self.all_store['static_attribute'][attr_word])[0])


        query_alt = query_alt + '?pred ?obj .' + '\n' + '}'


        query_part_1 = """
            PREFIX prop: <http://smartKT/ns/properties#>
            PREFIX symbol: <http://smartKT/ns/symbol#>

            SELECT ?seq ?name ?class ?file ?type ?pred1 ?pred2 ?obj
            WHERE
            {
                ?varId prop:comment_token "%s" ;
                       prop:spelling ?name ;
                       prop:storage_class ?class ;
                       prop:type ?type ;
                       prop:isDef_file_line ?file ;
            """

        query_part_3 = """
            ?seq prop:var_id ?varId ;
            """

        query_part_4 = """
            ?pred1 ?obj1 ;
            """

        query_part_5 = """
            ?pred2 ?obj .
            """

        query_part_6 = """
            FILTER (?pred1 IN (prop:NONLOCALREAD, prop:NONLOCALWRITE)).
            """

        query_part_7 = """
            FILTER (?pred2 IN (prop:RUNID, prop:INP, prop:posix_lock, prop:file_location) ) .
            FILTER strStarts(str(?varId),str(symbol:)) .
            """

        if call_flag:

            for ind,matched_tokens in enumerate(word_store['comment_token']):

                arguments = [matched_tokens[1]] + all_attr_list
                arguments = tuple(arguments)
                result_comment_first = defaultdict(dict)

                query = query_alt % arguments
                print(query)
                start_time = time.time()
                resultFirst = graph.query(query)
                end_time = time.time()
                # print("Time taken to process query",+end_time-start_time)

                for row in resultFirst:
                    print('syntactical match :' +matched_tokens[1])
                    curr_id = row['id'].split('#')[1]
                    if curr_id in result_comment_first:
                        result_comment_first[curr_id][str(row['pred'].split('#')[1])] = str(row['obj'])
                    else:
                        result_comment_first[curr_id][str(row['pred'].split('#')[1])] = str(row['obj'])
                        result_comment_first[curr_id]['match_name'] = matched_tokens[1]
                        result_comment_first[curr_id]['match_location'] = 'comments'

                if result_comment_first:
                    for key in result_comment_first:
                        if 'spelling' in result_comment_first[key]:
                            ans += 'Identifier name : ' + result_comment_first[key]['spelling'] + '\n'
                        if 'storage_class' in result_comment_first[key]:
                           ans += 'Storage class : ' + result_comment_first[key]['storage_class'] + '\n'
                        if 'type' in result_comment_first[key]:
                            ans += 'Datatype : ' + result_comment_first[key]['type'] + '\n'
                        if 'isDef_file_line' in result_comment_first[key]:
                            ans += 'Definition file : ' + result_comment_first[key]['isDef_file_line'] + '\n'
                        if 'isWritten_file_line' in result_comment_first[key]:
                            ans += 'Written in file : ' + result_comment_first[key]['isWritten_file_line'] + '\n'
                        if 'isRead_file_line' in result_comment_first[key]:
                            ans += 'Read in file : ' + result_comment_first[key]['isRead_file_line'] + '\n'
                        if 'is_a' in result_comment_first[key]:
                            ans += 'Identifier type : ' + result_comment_first[key]['is_a'] + '\n'
                        ans += 'Match name : ' + result_comment_first[key]['match_name'] + '\n'
                        ans += 'Match location : ' + result_comment_first[key]['match_location'] + '\n\n'

        else:

            for ind,matched_tokens in enumerate(word_store['comment_token']):

                arguments = (matched_tokens[1])

                if ind < self.syntax_count and matched_tokens[1]!='callback':

                    result = defaultdict(dict)
                    res = False
                    syn_flag = False

                    print('Syntactic '+matched_tokens[1]+'\n')

                    word = word_store['common_word'][0][0]
                    tag_list = self.all_store['common_word'][word]

                    for tag in tag_list:
                        query_part_2 = 'prop:is_a' + ' ' + '"' + str(tag) + '"' + '.' + '\n'
                        query = query_part_1 + query_part_2 + query_part_3

                        if rw_flag:
                            query = query + query_part_4 + query_part_5 + query_part_6 + query_part_7 + '\n' + '}'
                        else:
                            query = query + query_part_5 + query_part_7 + '\n' + '}'

                        print(arguments)

                        query = query % arguments
                        print(query)
                        start_time = time.time()
                        resultFirst = graph.query(query)
                        end_time = time.time()
                        print("Time taken to process query",+end_time-start_time)

                        curr_seq = ''

                        for row in resultFirst:
                            res = True
                            curr_seq = row['seq'].split('#')[1]
                            if curr_seq in result:
                                result[int(curr_seq)][str(row['pred2'].split('#')[1])] = str(row['obj'])
                            else:
                                stat = True
                                result[int(curr_seq)]['name'] = str(row['name'])
                                result_static[str(row['name'])]['storage class'] = str(row['class'])
                                result_static[str(row['name'])]['datatype'] = str(row['type'])
                                result_static[str(row['name'])]['isDef_file_line'] = str(row['file'])
                                result[int(curr_seq)][str(row['pred2'].split('#')[1])] = str(row['obj'])
                                result[int(curr_seq)][str(row['pred1'].split('#')[1])] = str(row['obj'])

                    result = OrderedDict(sorted(result.items()))

                    print(len(result))

                    if res:
                        ans += 'Corresponding to match name : '+ matched_tokens[1] + '\n\n'

                    for seq in result:
                        if 'name' in result[seq]:
                            ans += 'Identifier name : ' + result[seq]['name'] + '\n'
                        ans += 'Sequence no : ' + str(seq) + '\n'
                        if 'NONLOCALREAD' in result[seq]:
                           ans += 'Read : ' + 'True' + '\n'
                           if 'file_location' in result[seq]:
                                ans += 'Read made in file : ' + result[seq]['file_location'] + '\n'
                        if 'NONLOCALWRITE' in result[seq]:
                            ans += 'Write : ' + 'True' + '\n'
                            if 'file_location' in result[seq]:
                                ans += 'Write made in file : ' + result[seq]['file_location'] + '\n'
                        if 'INP' in result[seq]:
                            ans += 'Input name : ' + 'bar.png' + '\n'
                        if 'RUNID' in result[seq]:
                            ans += 'Run id : ' + '1' + '\n'
                        for key in result[seq]:
                            if key!='name' and key!='NONLOCALREAD' and key!='NONLOCALWRITE' and key!='file_location' and key!='INP' and key!='RUNID':
                                ans += key + ' : ' + result[seq][key] + '\n'

                        ans += '\n'

                else:
                    if count < 2 and matched_tokens[1]!='callback':

                        result = defaultdict(dict)
                        res = False
                        sem_flag = False

                        count = count + 1

                        print('Semantical '+matched_tokens[1]+'\n')

                        word = word_store['common_word'][0][0]
                        tag_list = self.all_store['common_word'][word]

                        for tag in tag_list:
                            query_part_2 = 'prop:is_a' + ' ' + '"' + str(tag) + '"' + '.' + '\n'
                            query = query_part_1 + query_part_2 + query_part_3

                            if rw_flag:
                                query = query + query_part_4 + query_part_5 + query_part_6 + query_part_7 + '\n' + '}'
                            else:
                                query = query + query_part_5 + query_part_7 + '\n' + '}'

                            if call_flag:
                                query = query_alt

                            query = query % arguments
                            print(query)
                            start_time = time.time()
                            resultFirst = graph.query(query)
                            end_time = time.time()
                            print("Time taken to process query",+end_time-start_time)

                            curr_seq = ''

                            for row in resultFirst:
                                res = True
                                curr_seq = row['seq'].split('#')[1]
                                if curr_seq in result:
                                    result[int(curr_seq)][str(row['pred2'].split('#')[1])] = str(row['obj'])
                                else:
                                    stat = True
                                    result[int(curr_seq)]['name'] = str(row['name'])
                                    result_static[str(row['name'])]['storage class'] = str(row['class'])
                                    result_static[str(row['name'])]['datatype'] = str(row['type'])
                                    result_static[str(row['name'])]['isDef_file_line'] = str(row['file'])
                                    result[int(curr_seq)][str(row['pred2'].split('#')[1])] = str(row['obj'])
                                    result[int(curr_seq)][str(row['pred1'].split('#')[1])] = str(row['obj'])

                        result = OrderedDict(sorted(result.items()))

                        print(len(result))

                        if res:
                            ans += 'Corresponding to match name : '+ matched_tokens[1] + '\n\n'

                        for seq in result:
                            if 'name' in result[seq]:
                                ans += 'Identifier name : ' + result[seq]['name'] + '\n'
                            ans += 'Sequence no : ' + str(seq) + '\n'
                            if 'NONLOCALREAD' in result[seq]:
                               ans += 'Read : ' + 'True' + '\n'
                               if 'file_location' in result[seq]:
                                    ans += 'Read made in file : ' + result[seq]['file_location'] + '\n'
                            if 'NONLOCALWRITE' in result[seq]:
                                ans += 'Write : ' + 'True' + '\n'
                                if 'file_location' in result[seq]:
                                    ans += 'Write made in file : ' + result[seq]['file_location'] + '\n'
                            if 'INP' in result[seq]:
                                ans += 'Input name : ' + 'bar.png' + '\n'
                            if 'RUNID' in result[seq]:
                                ans += 'Run id : ' + '1' + '\n'
                            for key in result[seq]:
                                if key!='name' and key!='NONLOCALREAD' and key!='NONLOCALWRITE' and key!='file_location' and key!='INP' and key!='RUNID':
                                    ans += key + ' : ' + result[seq][key] + '\n'

                            ans += '\n'

            if stat:
                ans += 'More information on the matched identifiers' +'\n\n'

            for seq in result_static:
                ans += 'Identifier name : ' + str(seq) + '\n'
                if 'storage class' in result_static[seq]:
                   ans += 'Storage class : ' + result_static[seq]['storage class'] + '\n'
                if 'datatype' in result_static[seq]:
                    ans += 'Datatype : ' + result_static[seq]['datatype'] + '\n'
                if 'isDef_file_line' in result_static[seq]:
                    ans += 'Definition file : ' + result_static[seq]['isDef_file_line'] + '\n'

                ans += '\n'

        return ans


    #which variables are accessed using mutex / which variables associated with concept are accessed using mutex
    def template_dynamic_attr_common(self,word_store,graph):

        ans = ''
        comment_name = ''
        result_dict = defaultdict(dict)

        if 'comment_token' in word_store:
            for matched_comment in word_store['comment_token']:
                comment_name = matched_comment[1]
                break

        query_part_1 = """
            PREFIX prop: <http://smartKT/ns/properties#>
            PREFIX symbol: <http://smartKT/ns/symbol#>

            SELECT DISTINCT ?id ?pred ?obj
            WHERE
            {
                ?seq prop:var_id ?id ;
                     prop:posix_lock "MUTEX" .
                ?id ?pred ?obj ;
            """

        query_part_2 = 'prop:comment_token' + ' ' + '"' + comment_name + '"' + ';' + '\n'

        query_part_4 = """
            FILTER (?pred IN (prop:storage_class, prop:isDef_file_line, prop:type, prop:spelling, prop:is_a) ) .
            }
            """

        for matched_word in word_store['common_word']:
            word = matched_word[0]
            tag_list = self.all_store['common_word'][word]

            for tag in tag_list:
                query_part_3 = 'prop:is_a' + ' ' + '"' + str(tag) + '"' + '.' + '\n'

                if comment_name:
                    query = query_part_1 + query_part_2 + query_part_3 + query_part_4
                else:
                    query = query_part_1 + query_part_3 + query_part_4
                print(query)

                start_time = time.time()
                result = graph.query(query)
                end_time = time.time()
                print("Time taken to process query",+end_time-start_time)

                prev_id = None
                ans_temp = ''
                count = 0

                for row in result:
                    curr_id = row['id'].split('#')[1]
                    result_dict[curr_id][str(row['pred'].split('#')[1])] = str(row['obj'])
                    if comment_name:
                        result_dict[curr_id]['match_name'] = comment_name

        for key in result_dict:
            if 'spelling' in result_dict[key]:
                ans += 'Identifier name : ' + result_dict[key]['spelling'] + '\n'
            if 'storage_class' in result_dict[key]:
               ans += 'Storage class : ' + result_dict[key]['storage_class'] + '\n'
            if 'type' in result_dict[key]:
                ans += 'Datatype : ' + result_dict[key]['type'] + '\n'
            if 'isDef_file_line' in result_dict[key]:
                ans += 'Definition file : ' + result_dict[key]['isDef_file_line'] + '\n'
            if 'is_a' in result_dict[key]:
                ans += 'Identifier type : ' + result_dict[key]['is_a'] + '\n'
            if 'match_name' in result_dict[key]:
                ans += 'Match name : ' + result_dict[key]['match_name'] + '\n'
            ans += 'Posix lock : Mutex' + '\n'

            ans += '\n'

        return ans

    #read write sequence of variable nstop
    def template_dynamic_attr_common_symbol(self,word_store,graph):

        ans = ''
        rw_flag = False
        result = defaultdict(dict)
        result_static = defaultdict(dict)

        if len(word_store['common_word']) > 1:
            ans = self.template_dynamic_attr_multi_common_symbol(word_store,graph)
            return ans

        for matched_attr in word_store['dynamic_attribute']:
            if matched_attr[0] == "read-write" or matched_attr[0] == "read write" or matched_attr[0] == "read" or matched_attr[0] == "write":
                rw_flag = True
                break

        for matched_symbol in word_store['symbol']:
            symbol_name = matched_symbol[1]
            break

        query_part_1 = """
            PREFIX prop: <http://smartKT/ns/properties#>
            PREFIX symbol: <http://smartKT/ns/symbol#>

            SELECT ?seq ?name ?class ?type ?file ?pred1 ?pred2 ?obj
            WHERE
            {
                ?varId prop:spelling "%s" ;
                       prop:storage_class ?class ;
                       prop:type ?type ;
                       prop:isDef_file_line ?file ;
            """

        query_part_3 = """
            ?seq prop:var_id ?varId ;
            """

        query_part_4 = """
            ?pred1 ?obj1 ;
            """

        query_part_5 = """
            ?pred2 ?obj .
            """

        query_part_6 = """
            FILTER (?pred1 IN (prop:NONLOCALREAD, prop:NONLOCALWRITE)).
            """

        query_part_7 = """
            FILTER (?pred2 IN (prop:RUNID, prop:INP, prop:posix_lock) ) .
            """

        word = word_store['common_word'][0][0]
        tag_list = self.all_store['common_word'][word]

        for tag in tag_list:
            query_part_2 = 'prop:is_a' + ' ' + '"' + str(tag) + '"' + '.' + '\n'
            query = query_part_1 + query_part_2 + query_part_3

            if rw_flag:
                query = query + query_part_4 + query_part_5 + query_part_6 + query_part_7 + '\n' + '}'
            else:
                query = query + query_part_5 + query_part_7 + '\n' + '}'

            query = query % (symbol_name)
            print(query)
            start_time = time.time()
            resultFirst = graph.query(query)
            end_time = time.time()
            print("Time taken to process query",+end_time-start_time)

            for row in resultFirst:
                res = True
                curr_seq = row['seq'].split('#')[1]
                if curr_seq in result:
                    result[int(curr_seq)][str(row['pred2'].split('#')[1])] = str(row['obj'])
                else:
                    stat = True
                    result[int(curr_seq)]['name'] = str(symbol_name)
                    result_static[symbol_name]['storage class'] = str(row['class'])
                    result_static[symbol_name]['datatype'] = str(row['type'])
                    result_static[symbol_name]['isDef_file_line'] = str(row['file'])
                    result[int(curr_seq)][str(row['pred2'].split('#')[1])] = str(row['obj'])
                    result[int(curr_seq)][str(row['pred1'].split('#')[1])] = str(row['obj'])

        result = OrderedDict(sorted(result.items()))

        if stat:
            ans += 'More information on the identifier' +'\n\n'

        for seq in result_static:
            ans += 'Identifier name : ' + str(seq) + '\n'
            if 'storage class' in result_static[seq]:
               ans += 'Storage class : ' + result_static[seq]['storage class'] + '\n'
            if 'datatype' in result_static[seq]:
                ans += 'Datatype : ' + result_static[seq]['datatype'] + '\n'
            if 'isDef_file_line' in result_static[seq]:
                ans += 'Definition file : ' + result_static[seq]['isDef_file_line'] + '\n'

            ans += '\n'

        for seq in result:
            ans += 'Sequence no : ' + str(seq) + '\n'
            if 'NONLOCALREAD' in result[seq]:
               ans += 'Read : ' + 'True' + '\n'
            if 'NONLOCALWRITE' in result[seq]:
                ans += 'Write : ' + 'True' + '\n'
            for key in result[seq]:
                if key!='name' and key!='NONLOCALREAD' and key!='NONLOCALWRITE':
                    ans += key + ' : ' + result[seq][key] + '\n'

            ans += '\n'

        return ans

    #read write sequence of variables in function trythis
    def  template_dynamic_attr_multi_common_symbol(self,word_store,graph):

        ans = ''
        rw_flag = False
        result = defaultdict(dict)

        for matched_attr in word_store['dynamic_attribute']:
            if matched_attr[0] == "read-write" or matched_attr[0] == "read write" or matched_attr[0] == "read" or matched_attr[0] == "write":
                rw_flag = True
                break

        for matched_symbol in word_store['symbol']:
            symbol_name = matched_symbol[1]

        query_part_1 = """
            PREFIX prop: <http://smartKT/ns/properties#>
            PREFIX symbol: <http://smartKT/ns/symbol#>

            SELECT ?seq ?name ?class ?file ?type ?pred2 ?obj
            WHERE
            {
                ?funcId prop:spelling "%s" ;
                        prop:linkage_name ?lname .
                ?varId prop:spelling ?name ;
                       prop:storage_class ?class ;
                       prop:isDef_file_line ?file ;
                       prop:type ?type .
            """

        query_part_2 = """
            ?seq prop:var_id ?varId ;
                 prop:func_name ?lname ;
            """

        query_part_4 = """
            ?pred1 ?obj1 ;
            """

        query_part_5 = """
            ?pred2 ?obj .
            """

        query_part_6 = """
            FILTER (?pred1 IN (prop:read_count, prop:write_count, prop:NONLOCALREAD, prop:NONLOCALWRITE)).
            """

        query_part_7 = """
            FILTER (?pred2 IN (prop:thread_id, prop:sync, prop:func_name, prop:RUNID, prop:INP, prop:posix_lock) ) .
            """

        query = query_part_1 + query_part_2

        if rw_flag:
            query = query + query_part_4 + query_part_5 + query_part_6 + query_part_7 + '\n' + '}'
        else:
            query = query + query_part_5 + query_part_7 + '\n' + '}'

        query = query % (symbol_name)
        print(query)
        start_time = time.time()
        resultFirst = graph.query(query)
        end_time = time.time()
        print("Time taken to process query",+end_time-start_time)

        count = 0

        for row in resultFirst:
            curr_seq = row['seq'].split('#')[1]
            if curr_seq in result:
                result[int(curr_seq)][str(row['pred2'].split('#')[1])] = str(row['obj'])
            else:
                count += 1
                if count > 6:
                    break
                print(count)
                print(int(curr_seq))
                result[int(curr_seq)]['name'] = str(row['name'])
                result[int(curr_seq)]['storage class'] = str(row['class'])
                result[int(curr_seq)]['datatype'] = str(row['type'])
                result[int(curr_seq)]['isDef_file_line'] = str(row['file'])
                result[int(curr_seq)][str(row['pred2'].split('#')[1])] = str(row['obj'])

        result = OrderedDict(sorted(result.items()))

        for seq in result:
            ans += 'Sequence no : ' + str(seq) + '\n'
            if 'name' in result[seq]:
                ans += 'Identifier name : ' + result[seq]['name'] + '\n'
            if 'storage class' in result[seq]:
               ans += 'Storage class : ' + result[seq]['storage class'] + '\n'
            if 'datatype' in result[seq]:
                ans += 'Datatype : ' + result[seq]['datatype'] + '\n'
            if 'isDef_file_line' in result[seq]:
                ans += 'Definition file : ' + result[seq]['isDef_file_line'] + '\n'
            for key in result[seq]:
                if key!='name' and key!='storage class' and key!='datatype' and key!='isDef_file_line':
                    ans += key + ' : ' + result[seq][key] + '\n'

            ans += '\n'

        return ans

    #read write sequence of variable __ in file __
    def template_dynamic_attr_common_symbol_file(self,word_store,graph):

        ans = ''
        rw_flag = False
        result = defaultdict(dict)

        for matched_attr in word_store['dynamic_attribute']:
            if matched_attr[0] == "read-write" or matched_attr[0] == "read write" or matched_attr[0] == "read" or matched_attr[0] == "write":
                rw_flag = True
                break

        for matched_symbol in word_store['symbol']:
            symbol_name = matched_symbol[1]
            if symbol_name != 'file':
                break

        for matched_symbol in word_store['fil']:
            file_name = matched_symbol[1]
            break

        query_part_1 = """
            PREFIX prop: <http://smartKT/ns/properties#>
            PREFIX symbol: <http://smartKT/ns/symbol#>

            SELECT ?seq ?name ?class ?type ?pred2 ?obj
            WHERE
            {
                ?varId prop:spelling "%s" ;
                       prop:is_defined_file "%s" ;
                       prop:storage_class ?class ;
                       prop:type ?type ;
            """

        query_part_3 = """
            ?seq prop:var_id ?varId ;
            """

        query_part_4 = """
            ?pred1 ?obj1 ;
            """

        query_part_5 = """
            ?pred2 ?obj .
            """

        query_part_6 = """
            FILTER (?pred1 IN (prop:read_count, prop:write_count, prop:NONLOCALREAD, prop:NONLOCALWRITE)).
            """

        query_part_7 = """
            FILTER (?pred2 IN (prop:thread_id, prop:sync, prop:func_name, prop:RUNID, prop:INP, prop:posix_lock) ) .
            """

        ans += '\n'+'Result ' + ':' + '\n'

        word = word_store['common_word'][0][0]
        tag_list = self.all_store['common_word'][word]

        for tag in tag_list:
            query_part_2 = 'prop:is_a' + ' ' + '"' + str(tag) + '"' + '.' + '\n'
            query = query_part_1 + query_part_2 + query_part_3

            if rw_flag:
                query = query + query_part_4 + query_part_5 + query_part_6 + query_part_7 + '\n' + '}'
            else:
                query = query + query_part_5 + query_part_7 + '\n' + '}'

            query = query % (symbol_name,file_name)
            print(query)
            start_time = time.time()
            resultFirst = graph.query(query)
            end_time = time.time()
            print("Time taken to process query",+end_time-start_time)

            count = 0

            for row in resultFirst:
                curr_seq = row['seq'].split('#')[1]
                print(curr_seq)
                if curr_seq in result:
                    result[int(curr_seq)][str(row['pred2'].split('#')[1])] = str(row['obj'])
                else:
                    count += 1
                    if count >= 10:
                        break
                    result[int(curr_seq)]['storage class'] = str(row['class'])
                    result[int(curr_seq)]['datatype'] = str(row['type'])
                    result[int(curr_seq)][str(row['pred2'].split('#')[1])] = str(row['obj'])


        result = OrderedDict(sorted(result.items()))

        for seq in result:
            if 'storage class' in result[seq]:
               ans += 'Storage class : ' + result[seq]['storage class'] + '\n'
            if 'datatype' in result[seq]:
                ans += 'Datatype : ' + result[seq]['datatype'] + '\n'

            for key in result[seq]:
                if key!='name' and key!='storage class' and key!='datatype' and key!='match_name':
                    ans += key + ' : ' + result[seq][key] + '\n'

            ans += '\n'

        return ans

    #How many unsynchronised accesses are there in file pngtest.c
    def template_dynamic_attr_file(self,word_store,graph):

        ans = ''
        sync_val = ''
        val_flag = False
        result_dict = defaultdict(dict)

        for matched_attr in word_store['dynamic_attribute']:
            if matched_attr[0] == 'unsynchronised' or matched_attr[0] == 'asynchronised' or matched_attr[0] == 'asynchronous' or matched_attr[0] == 'unsynchronized' or matched_attr[0] == 'asynchronized':
                sync_val = 'ASYNC'
            else:
                sync_val = '3'

        for matched_file in word_store['fil']:
            file_name = matched_file[1]


        if 'values' in word_store:
            val_flag = True
            for matched_val in word_store['values']:
                val = matched_val[0]
                attr = list(self.all_store['values'][val])[0]
                query_part_4 = 'prop:%s' % attr + ' ' + '"' + val + '"' + ';' + '\n'


        query_part_1 = """
            PREFIX prop: <http://smartKT/ns/properties#>
            PREFIX symbol: <http://smartKT/ns/symbol#>

            SELECT DISTINCT ?id ?pred1 ?obj1
            WHERE
            {
                ?seq prop:sync "%s";
            """

        query_part_2 = """
                     prop:func_name ?name .
                     """

        query_part_2_1 = """
                     prop:var_name ?name .
                     """

        query_part_3 = """
                ?id prop:linkage_name ?name;
                    prop:is_defined_file "%s";
            """

        query_part_5 = """
                    ?pred1 ?obj1 .
            """


        query_part_6 = """
            FILTER (?pred1 IN (prop:storage_class, prop:type, prop:spelling, prop:is_a, prop:isDef_file_line) ) .
            }
            """

        if val_flag:
            query = query_part_1 + query_part_2_1 + query_part_3 + query_part_4 + query_part_5 + query_part_6
        else:
            query = query_part_1 + query_part_2 + query_part_3 + query_part_5 + query_part_6

        query = query % (sync_val,file_name)
        print(query)
        start_time = time.time()
        resultFirst = graph.query(query)
        end_time = time.time()
        print("Time taken to process query",+end_time-start_time)

        print(resultFirst)
        sys.stdout.flush()

        count = 0

        for row in resultFirst:
            curr_id = row['id'].split('#')[1]
            if curr_id in result_dict:
                result_dict[curr_id][str(row['pred1'].split('#')[1])] = str(row['obj1'])
            else:
                count += 1
                if count > 5:
                    break
                print(count)
                print(curr_id)
                result_dict[curr_id][str(row['pred1'].split('#')[1])] = str(row['obj1'])

        for key in result_dict:
            if 'spelling' in result_dict[key]:
                ans += 'Identifier name : ' + result_dict[key]['spelling'] + '\n'
            if 'storage_class' in result_dict[key]:
               ans += 'Storage class : ' + result_dict[key]['storage_class'] + '\n'
            if 'type' in result_dict[key]:
                ans += 'Datatype : ' + result_dict[key]['type'] + '\n'
            if 'isDef_file_line' in result_dict[key]:
                ans += 'Definition file : ' + result_dict[key]['isDef_file_line'] + '\n'
            if 'is_a' in result_dict[key]:
                ans += 'Identifier type : ' + result_dict[key]['is_a'] + '\n'
            if 'match_name' in result_dict[key]:
                ans += 'Match name : ' + result_dict[key]['match_name'] + '\n'
            if sync_val == 'ASYNC':
                ans += 'Synchronisation : ASYNC' + '\n'
            else:
                 ans += 'Synchronisation : SYNC' + '\n'

            ans += '\n'

        return ans

    # How many static variables have unsynchronised accesses in file pngtest.c?
    def template_value_common_dynamic_attr_file(self,word_store,graph):

        ans = ''
        sync_val = ''
        comment_name = ''
        result_dict = defaultdict(dict)
        val_flag = False

        if 'comment_token' in word_store:
            for matched_comment in word_store['comment_token']:
                comment_name = matched_comment[1]
                break

        for matched_attr in word_store['dynamic_attribute']:
            if matched_attr[0] == 'unsynchronised' or matched_attr[0] == 'asynchronised' or matched_attr[0] == 'asynchronous' or matched_attr[0] == 'unsynchronized' or matched_attr[0] == 'asynchronized':
                sync_val = 'ASYNC'
            else:
                sync_val = '1'

        for matched_file in word_store['fil']:
            file_name = matched_file[1]


        if 'values' in word_store:
            val_flag = True
            for matched_val in word_store['values']:
                val = matched_val[0]
                attr = list(self.all_store['values'][val])[0]
                query_part_4 = 'prop:%s' % attr + ' ' + '"' + val + '"' + ';' + '\n'


        query_part_1 = """
            PREFIX prop: <http://smartKT/ns/properties#>
            PREFIX symbol: <http://smartKT/ns/symbol#>

            SELECT DISTINCT ?id ?pred1 ?obj1
            WHERE
            {
                ?seq prop:sync "%s";
            """

        query_part_2_1 = """
                     prop:var_name ?name .
                     """

        query_part_3 = """
                ?id prop:spelling ?name;
                    prop:is_defined_file "%s";
            """

        query_part_4_1 = 'prop:comment_token' + ' ' + '"' + comment_name + '"' + ';' + '\n'

        query_part_5 = """
                    ?pred1 ?obj1 .
            """


        query_part_6 = """
            FILTER (?pred1 IN (prop:storage_class, prop:type, prop:spelling, prop:is_a, prop:isDef_file_line) ) .
            }
            """

        if comment_name:
            query = query_part_1 + query_part_2_1 + query_part_3 + query_part_4 + query_part_4_1 + query_part_5 + query_part_6
        else:
            query = query_part_1 + query_part_2_1 + query_part_3 + query_part_4 + query_part_5 + query_part_6


        query = query % (sync_val,file_name)
        print(query)
        start_time = time.time()
        resultFirst = graph.query(query)
        end_time = time.time()
        print("Time taken to process query",+end_time-start_time)


        print(resultFirst)
        sys.stdout.flush()
        count = 0

        for row in resultFirst:
            curr_id = row['id'].split('#')[1]
            if curr_id in result_dict:
                result_dict[curr_id][str(row['pred1'].split('#')[1])] = str(row['obj1'])
            else:
                count += 1
                if count > 5:
                    break
                print(count)
                print(curr_id)
                result_dict[curr_id][str(row['pred1'].split('#')[1])] = str(row['obj1'])
                if comment_name:
                    result_dict[curr_id]['match_name'] = comment_name

        for key in result_dict:
            if 'spelling' in result_dict[key]:
                ans += 'Identifier name : ' + result_dict[key]['spelling'] + '\n'
            if 'storage_class' in result_dict[key]:
               ans += 'Storage class : ' + result_dict[key]['storage_class'] + '\n'
            if 'type' in result_dict[key]:
                ans += 'Datatype : ' + result_dict[key]['type'] + '\n'
            if 'isDef_file_line' in result_dict[key]:
                ans += 'Definition file : ' + result_dict[key]['isDef_file_line'] + '\n'
            if 'is_a' in result_dict[key]:
                ans += 'Identifier type : ' + result_dict[key]['is_a'] + '\n'
            if 'match_name' in result_dict[key]:
                ans += 'Match name : ' + result_dict[key]['match_name'] + '\n'
            if sync_val == 'ASYNC':
                ans += 'Synchronisation : ASYNC' + '\n'
            else:
                 ans += 'Synchronisation : SYNC' + '\n'

            ans += '\n'

        return ans

    #read write sequence of variable __ in function __
    def template_dynamic_attr_common_symbol_common_symbol(self,word_store,graph):

        ans = ''
        rw_flag = False

        for matched_attr in word_store['dynamic_attribute']:
            if matched_attr[0] == "read-write" or matched_attr[0] == "read write" or matched_attr[0] == "read" or matched_attr[0] == "write":
                rw_flag = True
                break

        query_part_1 = """
            PREFIX prop: <http://smartKT/ns/properties#>
            PREFIX symbol: <http://smartKT/ns/symbol#>

            SELECT ?seq ?class ?type ?file ?pred2 ?obj
            WHERE
            {
                ?funcId prop:spelling "%s" ;
                        prop:linkage_name ?lname .
                ?varId prop:spelling "%s" ;
                       prop:storage_class ?class ;
                       prop:type ?type ;
                       prop:isDef_file_line ?file .
            """

        query_part_2 = """
            ?seq prop:var_id ?varId ;
                 prop:func_name ?lname ;
            """

        query_part_4 = """
            ?pred1 ?obj1 ;
            """

        query_part_5 = """
            ?pred2 ?obj .
            """

        query_part_6 = """
            FILTER (?pred1 IN (prop:read_count, prop:write_count, prop:NONLOCALREAD, prop:NONLOCALWRITE)).
            """

        query_part_7 = """
            FILTER (?pred2 IN (prop:thread_id, prop:sync, prop:func_name, prop:RUNID, prop:INP, prop:posix_lock) ) .
            """

        query = query_part_1 + query_part_2

        if rw_flag:
            query = query + query_part_4 + query_part_5 + query_part_6 + query_part_7 + '\n' + '}'
        else:
            query = query + query_part_5 + query_part_7 + '\n' + '}'

        symbol_perm = permutations(word_store['symbol'], 2)

        for symbol_names in symbol_perm:

            result = defaultdict(dict)
            queryFirst = query % (symbol_names[0][0],symbol_names[1][0])
            print(queryFirst)
            start_time = time.time()
            resultFirst = graph.query(queryFirst)
            end_time = time.time()
            print("Time taken to process query",+end_time-start_time)

            count = 0

            for row in resultFirst:
                curr_seq = int(row['seq'].split('#')[1])
                if curr_seq in result:
                    result[int(curr_seq)][str(row['pred2'].split('#')[1])] = str(row['obj'])
                else:
                    count += 1
                    if count > 5:
                        break
                    print(count)
                    print(curr_seq)
                    result[int(curr_seq)]['storage class'] = str(row['class'])
                    result[int(curr_seq)]['datatype'] = str(row['type'])
                    result[int(curr_seq)]['isDef_file_line'] = str(row['file'])
                    result[int(curr_seq)][str(row['pred2'].split('#')[1])] = str(row['obj'])

            result = OrderedDict(sorted(result.items()))

            for seq in result:
                ans += 'Sequence no : ' + str(seq) + '\n'
                if 'storage class' in result[seq]:
                   ans += 'Storage class : ' + result[seq]['storage class'] + '\n'
                if 'datatype' in result[seq]:
                    ans += 'Datatype : ' + result[seq]['datatype'] + '\n'
                if 'isDef_file_line' in result[seq]:
                    ans += 'Definition file : ' + result[seq]['isDef_file_line'] + '\n'
                for key in result[seq]:
                    if key!='name' and key!='storage class' and key!='datatype' and key!='match_name' and key!='isDef_file_line':
                        ans += key + ' : ' + result[seq][key] + '\n'

                ans += '\n'

        return ans


    #we serach in the program dictionary
    def search_program_dict(self,words,graph):

        ans = ''
        word_store = defaultdict(list)
        search_program = False

        #search in program dictionary keys
        for word in words:
            if word in self.program_domain_dict:
                search_program = True
                program = word
                break

        if not search_program:
            return ans
        else:
            for word in self.program_domain_dict[program]:
                word_store['name_token'].append(('',word))
                word_store['comment_token'].append(('',word))
            ans = self.template_comment_token(word_store,graph)
            if ans:
                return ans
            else:
                ans = self.template_name_token(word_store,graph)
                return ans


    #run all the functions in this file and finally give response back to the file "init.py"
    def execute_query(self,graph,TTLfile,RegexFile,query):

        global prev_symbol_list
        global curr_symbol_list

        all_regex = self.make_list(RegexFile)

        new_query = self.filter_query_words(query)
        print(new_query)

        word_store, new_query, words = self.search_matched_words(new_query)

        #if no keys matched with any query word we try as our last resort in the program dictionary
        if len(word_store)==0:
            ans = self.search_program_dict(words,graph)
            if not ans:
               return "Please enter a valid query or kindly try a different way to write your query."
            return ans

        new_query = self.insert_placeholders_in_query(words,new_query,word_store)
        print(new_query)

        matched_regex_list = self.regex_match(all_regex,new_query)
        print(matched_regex_list)

        if(len(matched_regex_list)==0):
            return "Please enter a valid query or kindly try a different way to write your query."
        else:
            ans = self.call_matched_template_function(word_store,matched_regex_list,graph)

            #update our previous symbol list if we get new symbols in the current symbol lists
            if len(curr_symbol_list['symbol']) >= 1:
                prev_symbol_list['symbol'] = curr_symbol_list['symbol'][:1]
            if len(curr_symbol_list['name_token']) >= 1:
                prev_symbol_list['name_token'] = curr_symbol_list['name_token'][:1]

        return ans


    def execute_query_file(self,graph,TTLfile,RegexFile,query_file):

        fp = open(query_file,'r')
        ans = ''

        for query in fp:
            print(query)
            res = self.execute_query(graph,TTLfile,RegexFile,query)

            ans += res
            ans += '\n'

        return ans



# if __name__ == "__main__":

#   parser = argparse.ArgumentParser(description='Files needed to run the code.')
#   parser.add_argument(dest='TTLfile', action='store', help='Input the TTL file')
#   parser.add_argument(dest='XMLFile', action='store', help='Input the XML file')
#   args = vars(parser.parse_args())
#   TTLfile = args['TTLfile']
#   XMLFile = args['XMLFile']
