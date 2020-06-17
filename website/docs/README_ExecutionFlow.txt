Following is the code flow execution for Libpng project. Kindly change the file names where needed.


*TTL Generation :

Go to the parseXML folder in code files.


1) Execute the file mapping_extra_id.py to create the lookup dictionary.

Input is : final_static.xml
Output is : mapping_libpng_static.p

Execution command is : python mapping_extra_id.py ../../xml_csv_files/libpng_xml/final_static.xml ../../Data\ files/mapping_libpng_static.p


2) Execute the file parseStaticXML.py to create TTL corresponding to the static XML. It also creates a csv file which has all the name tokens.

Input is : final_static.xml, mapping_libpng_static.p
Output is : final_static.ttl, name_tokens.csv, libpng_files.p

Execution command is : python parseStaticXML.py ../../xml_csv_files/libpng_xml/final_static.xml ../../TTL\ files/libpng\ TTL/final_static.ttl ../../Data\ files/mapping_libpng_static.p


3) Execute the file parseDynamicXML.py to create TTL corresponding to the dynamic XML.

Input is : final_dynamic_1.xml, mapping_libpng_static.p
Output is : final_dynamic.ttl

Execution command is : python parseDynamicXML.py ../../xml_csv_files/libpng_xml/final_dynamic_1.xml ../../TTL\ files/libpng\ TTL/final_dynamic.ttl ../../Data\ files/mapping_libpng_static.p


4) Execute the file parseCommentXML.py to create TTL corresponding to the comments XML. It also creates a csv file which has all the comment tokens.

Input is : final_comments.xml, mapping_libpng_static.p
Output is : final_comments.ttl, comment_tokens.csv

Execution command is : python parseCommentXML.py ../../xml_csv_files/libpng_xml/final_comments.xml ../../TTL\ files/libpng\ TTL/final_comments.ttl ../../Data\ files/mapping_libpng_static.p


5) Execute the file merge.py - reads all the three static, dynamic and comments TTL files and merges them into one.

Input is : final_static.ttl, final_dynamic.ttl, final_comments.ttl
Output is : final.ttl

Execution command is : python merge.py ../../TTL\ files/libpng\ TTL/final_static.ttl ../../TTL\ files/libpng\ TTL/final_dynamic.ttl ../../TTL\ files/libpng\ TTL/final_comments.ttl ../../TTL\ files/libpng\ TTL/final.ttl



*Create the placeholder dictionary (all_store)


Execute the file all_store.py to create all_store file.

Input is : final_static.xml, final_comments.xml
Output is : libpng_all_store.p

Execution command is : python all_store.py ../xml_csv_files/libpng_xml/final_static.xml ../xml_csv_files/libpng_xml/final_comments.xml



*Create the Similarity Dictionaries


Go to the similarity_tokens_dict folder in code files.


1) feed the similarity model with name_tokens.csv to get similar name tokens and remove the concept column and store as name_token_similar.csv
2) Similarly feed the similarity model with comment_tokens.csv to get similar comment tokens and remove the concept column and store as comment_token_similar.csv


3) Execute the file name_tokens_dict.py to create a dictionary of name tokens with their similar tokens stored from most similar to least.

name_top10_similar_model_200_W10_CBOW_NEG5.csv (output from the similarity model for name_tokens.csv) should be in the same folder as the file.

Output : libpng_name_tokens_dict.p

Execution command is : python name_tokens_dict.py


4) Execute the file comment_tokens_dict.py to create a dictionary of comment tokens with their similar tokens stored from most similar to least.

comment_top10_similar_model_200_W10_CBOW_NEG5.csv (output from the similarity model for comment_tokens.csv) should be in the same folder as the file.

Output : libpng_comment_tokens_dict.p

Execution command is : python comment_tokens_dict.py


5) Execute the file program_domain_dict.py to create a dictionary of concepts with their similar concepts stored from most similar to least.

crossSimilarity_matrix.csv should be in the same folder as the file.

Output : libpng_program_domain_dict.p

Execution command is : python program_domain_dict.py



*Query System

Execute the file init.py in folder SErver_files.

Execution command is : python init.py
