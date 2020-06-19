import sys, os, json
import nltk

nltk.download('averaged_perceptron_tagger')

# Read the config file
config = json.loads(open("web_config.json", "r").read())

# Define some paths
data_abs_path = os.path.abspath('data')
generated_abs_path = os.path.abspath('generated')
models_abs_path = os.path.abspath('models')

# Execution Flow (For details, see 'docs')

# All Store
os.system(' '.join(["python3", "helpers/data_processing/all_store.py",
 os.path.join(data_abs_path, "final_static.xml"),
 os.path.join(data_abs_path, "final_comments.xml"),
 os.path.join(generated_abs_path, "all_store.p")]))


## TTL Generation
# mapping
os.system(' '.join(["python3", "helpers/data_processing/parseXML/mapping_extra_id.py",
 os.path.join(data_abs_path, "final_static.xml"),
 os.path.join(generated_abs_path, "mapping_static.p")]))

# static
os.system(' '.join(["python3", "helpers/data_processing/parseXML/parseStaticXML.py",
 os.path.join(data_abs_path, "final_static.xml"),
 os.path.join(generated_abs_path, "mapping_static.p"),
 os.path.join(generated_abs_path, "final_static.ttl"),
 os.path.join(generated_abs_path, "name_tokens.csv"),
 os.path.join(generated_abs_path, "name_tokens.p"),
 os.path.join(generated_abs_path, "files.p")]))

# dynamic
if config['processDynamic']:
    os.system(' '.join(["python3", "helpers/data_processing/parseXML/parseDynamicXML.py",
     os.path.join(data_abs_path, "final_dynamic.xml"),
     os.path.join(generated_abs_path, "mapping_static.p"),
     os.path.join(generated_abs_path, "final_dynamic.ttl")]))

# comments
if config['processComments']:
    os.system(' '.join(["python3", "helpers/data_processing/parseXML/parseCommentXML.py",
     os.path.join(generated_abs_path, "all_store.p"),
     os.path.join(data_abs_path, "final_comments.xml"),
     os.path.join(generated_abs_path, "mapping_static.p"),
     os.path.join(generated_abs_path, "final_comments.ttl"),
     os.path.join(generated_abs_path, "comment_token_tagged.csv"),
     os.path.join(generated_abs_path, "comment_tokens.csv"),
     os.path.join(generated_abs_path, "comment_tokens.p")]))

# merge
mergeCMD = 'python3 helpers/data_processing/parseXML/merge.py ' + os.path.join(generated_abs_path, "final_static.ttl") + " "
if config['processDynamic']:
    mergeCMD += os.path.join(generated_abs_path, "final_dynamic.ttl") + " "
else:
    mergeCMD += "NONE "
if config['processComments']:
    mergeCMD += os.path.join(generated_abs_path, "final_comments.ttl") + " "
else:
    mergeCMD += "NONE "
mergeCMD += os.path.join(generated_abs_path, "final.ttl")
os.system(mergeCMD)

## Placeholder creation
# Name Tokens
os.system(' '.join(["python3", "helpers/data_processing/similarity_tokens_dict/top10sim.py",
 os.path.join(generated_abs_path, "name_tokens.csv"),
 os.path.join(models_abs_path, config['model']),
 os.path.join(generated_abs_path, "model_similar_name_tokens.csv")]))

os.system(' '.join(["python3", "helpers/data_processing/similarity_tokens_dict/name_tokens_dict.py",
 os.path.join(generated_abs_path, "model_similar_name_tokens.csv"),
 os.path.join(generated_abs_path, "similar_name_tokens.csv"),
 os.path.join(generated_abs_path, "name_tokens_dict.p")]))

# Comment Tokens
os.system(' '.join(["python3", "helpers/data_processing/similarity_tokens_dict/top10sim.py",
 os.path.join(generated_abs_path, "comment_tokens.csv"),
 os.path.join(models_abs_path, config['model']),
 os.path.join(generated_abs_path, "model_similar_comment_tokens.csv")]))

os.system(' '.join(["python3", "helpers/data_processing/similarity_tokens_dict/comment_tokens_dict.py",
 os.path.join(generated_abs_path, "model_similar_comment_tokens.csv"),
 os.path.join(generated_abs_path, "similar_comment_tokens.csv"),
 os.path.join(generated_abs_path, "comment_tokens_dict.p")]))

## TF-IDF Things
os.system(' '.join(["python3", "helpers/data_processing/tf_idf/name_file_token_count.py",
 os.path.join(generated_abs_path, "final_static.ttl"),
 os.path.join(generated_abs_path, "name_file_token_count.p")]))

os.system(' '.join(["python3", "helpers/data_processing/tf_idf/name_token_file_count.py",
 os.path.join(generated_abs_path, "name_tokens.p"),
 os.path.join(generated_abs_path, "final_static.ttl"),
 os.path.join(generated_abs_path, "name_token_file_count.p")]))

os.system(' '.join(["python3", "helpers/data_processing/tf_idf/symbol_file_token_count.py",
 os.path.join(generated_abs_path, "final_static.ttl"),
 os.path.join(generated_abs_path, "symbol_file_token_count.p")]))

os.system(' '.join(["python3", "helpers/data_processing/tf_idf/symbol_token_file_count.py",
 os.path.join(generated_abs_path, "all_store.p"),
 os.path.join(generated_abs_path, "final_static.ttl"),
 os.path.join(generated_abs_path, "symbol_token_file_count.p")]))

os.system(' '.join(["python3", "helpers/data_processing/tf_idf/tf_idf.py",
 os.path.join(generated_abs_path, "name_file_token_count.p"),
 os.path.join(generated_abs_path, "name_token_file_count.p"),
 os.path.join(generated_abs_path, "tf_idf_name_tokens.p")]))

os.system(' '.join(["python3", "helpers/data_processing/tf_idf/tf_idf.py",
 os.path.join(generated_abs_path, "symbol_file_token_count.p"),
 os.path.join(generated_abs_path, "symbol_token_file_count.p"),
 os.path.join(generated_abs_path, "tf_idf_symbol_tokens.p")]))

os.system(' '.join(["python3", "helpers/data_processing/overloaded_sibling.py",
 os.path.join(generated_abs_path, "final_static.ttl"),
 os.path.join(generated_abs_path, "test_overload_new.ttl")]))

## Program Domain Dict
os.system(' '.join(["python3", "helpers/data_processing/similarity_tokens_dict/crossSim.py",
 os.path.join(models_abs_path, config['model']),
 os.path.join(data_abs_path, "VocabDictionary.csv"),
 os.path.join(generated_abs_path, "crossSimilarity_matrix.csv")]))

os.system(' '.join(["python3", "helpers/data_processing/similarity_tokens_dict/program_domain_dict.py",
 os.path.join(generated_abs_path, "crossSimilarity_matrix.csv"),
 os.path.join(generated_abs_path, "program_domain_dict.p")]))

## CFG integration with dynamic data
os.system(' '.join(["python3", "helpers/cfg/aggregrate.py",
 os.path.join(data_abs_path, "final_static.xml"),
 os.path.join(data_abs_path, "final.cfg"),
 os.path.join(generated_abs_path, "cfg"),
 ' '.join([os.path.join(data_abs_path, x) for x in config['dumps']])]))
