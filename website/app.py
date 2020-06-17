from __future__ import print_function
from flask import Flask, render_template, make_response, Markup, flash
from flask import redirect, request, jsonify, url_for, send_file

import io, os, uuid, pickle, json, random, time, rdflib
from xml.etree.ElementTree import Element, SubElement
from xml.etree import ElementTree as ET
from xml.dom import minidom

from query_run import QueryConversion
from werkzeug.utils import secure_filename
from collections import defaultdict

DEBUG = True
TIME = True

app = Flask(__name__)
app.secret_key = 's3cr3t'
app.debug = True
app._static_folder = os.path.abspath("templates/static/")

config = json.loads(open("web_config.json", "r").read())

project_name = config['project_name']
CXX_EXTENSIONS = ['c', 'cpp', 'cc']

data_abs_path = os.path.abspath('data')
generated_abs_path = os.path.abspath('generated')

RegexFile = os.path.join(data_abs_path, 'regex.txt')
all_files = os.path.join(generated_abs_path, 'files.p')
all_name_tokens_dict = os.path.join(generated_abs_path, "name_tokens_dict.p")
all_comment_tokens_dict = os.path.join(generated_abs_path, 'comment_tokens_dict.p')
program_domain_dict = os.path.join(generated_abs_path, 'program_domain_dict.p')
all_store_file = os.path.join(generated_abs_path, 'all_store.p')
tf_idf_name_tokens = os.path.join(generated_abs_path, 'tf_idf_name_tokens.p')
tf_idf_symbol = os.path.join(generated_abs_path, 'tf_idf_symbol_tokens.p')
TTLfile = os.path.join(generated_abs_path, 'final.ttl')

graph = rdflib.Graph()
start_time = time.time()
graph.load(TTLfile, format='turtle')
end_time = time.time()
if TIME:
    print("Time taken to load TTL: ", end_time-start_time)

def to_dot (li, fn):
    with open(fn + '.dot', 'w') as fp:
        fp.write('digraph G{\n')
        for el in list(set(li)):
            if type(el) in [list, tuple]:
                fp.write('"{}"->"{}"[label="{}"]\n'.format(el[0], el[1], el[2]))
            else:
                fp.write('"{}"\n'.format(el))
        fp.write('}\n')
    os.system("sfdp -Tpng -Goverlap=prism {}.dot -o {}.png".format(fn, fn))

def shorten(path):
    ls = path.split('/')
    try:
        idx = ls.index(project_name)
    except:
        return os.path.join('build', path)
    return '/'.join(ls[idx+1:])

def create_dep_map(fillMe=None, toDot=True):
    dep = pickle.load(open("data/dependencies.p", "rb"))
    ls = []
    for d in dep:
        #[TODO]: Improve checking mechanism
        if d.split('.').count('o') > 0:
            ls.append((dep[d], d, "SRC"))
            continue
        ls.extend([(f, d, "OBJ") for f in dep[d] if f.split('.').count('o') > 0])
        ls.extend([(f, d, "SO/DL") for f in dep[d] if f.split('.').count('so') > 0])
        ls.extend([(f, d, "AR") for f in dep[d] if f.split('.').count('a') > 0])
    ls = [(shorten(d), shorten(f), t) for (d,f,t) in ls]
    if fillMe is not None:
        fillMe.extend(ls)
    if toDot is True:
        filename = "templates/static/images/dep"
        to_dot(ls, filename)
        return filename + ".png"

def structclassmap(root):
    #{TODO}: Handle Friends, Templates(?)
    ls = []

    # Do it for classes
    for c in root.findall(".//ClassDecl"):
        try:
            ls.append(c.attrib['spelling'])
        except:
            continue
        # Inheritance edges
        for p in c.findall("./CXXBaseClassSpecifier"):
            ls.append((c.attrib['spelling'], p.attrib['type'], p.attrib['inheritance_kind']))
        # Nested Classes and Structs:
        for p in c.findall("./ClassDecl"):
            ls.append((p.attrib['spelling'], c.attrib['spelling'], "Nested"))
        for p in c.findall("./StructDecl"):
            ls.append((p.attrib['spelling'], c.attrib['spelling'], "Nested"))
        # # dependency edges
        # for d in c.findall("./FIELD_DECL"):
        #     for t in d.findall(".//TYPE_REF"):
        #         ls.append((str(t.attrib['type'].split()[-1]), c.attrib['spelling'], d.attrib['access_specifier']))

    # Do it for structs
    for c in root.findall(".//StructDecl"):
        try:
            ls.append(c.attrib['spelling'])
        except:
            continue
        # Inheritance edges
        for p in c.findall("./CXXBaseClassSpecifier"):
            ls.append((c.attrib['spelling'], p.attrib['type'], p.attrib['inheritance_kind']))
        # Nested Classes and Structs:
        for p in c.findall("./ClassDecl"):
            ls.append((p.attrib['spelling'], c.attrib['spelling'], "Nested"))
        for p in c.findall("./StructDecl"):
            ls.append((p.attrib['spelling'], c.attrib['spelling'], "Nested"))

        # # dependency edges
        # for d in c.findall("./FIELD_DECL"):
        #     for t in d.findall(".//TYPE_REF"):
        #         ls.append((str(t.attrib['type'].split()[-1]), c.attrib['spelling'], d.attrib['access_specifier']))
    filename = "templates/static/images/classmap"
    to_dot(ls, filename)
    return filename + ".png"

def create_extern_link(ls, croot):
    for var in croot.findall(".//VarDecl[@storage_class='extern']"):
        if 'def_id' not in var.attrib:
            continue
        name = var.attrib['type']+ " " + var.attrib['spelling']
        ls.append((name, shorten(var.attrib['file']), "REFERED"))
        for x in croot.findall('.//VarDecl[@id="'+var.attrib['def_id']+'"]'):
            ls.append((name, shorten(x.attrib['file']), "DEFINED"))
    for func in croot.findall(".//FunctionDecl[@storage_class='extern']"):
        if 'def_id' not in func.attrib:
            continue
        name = func.attrib['type']+ " " + func.attrib['spelling']
        ls.append((name, shorten(func.attrib['file']), "REFERED"))
        for x in croot.findall('.//FunctionDecl[@id="'+func.attrib['def_id']+'"]'):
            ls.append((name, shorten(x.attrib['file']), "DEFINED"))

def visDOT(filename):
    with open(filename, "r") as f:
        data = f.readlines()
    data = [x.strip() for x in data]
    data = data[0]+'; '.join(data[1:-1])+"; }"
    return data

def addDOT(filename, line, col, data):
    with open(filename, 'r') as f:
        content = f.readlines()
    content[line] = content[line][:col] + "'" + data + "';\n"
    with open(filename, 'w') as f:
        f.write(''.join(content))

def getExecutables():
    dep = pickle.load(open("data/dependencies.p", "rb"))
    ls = []
    for k in dep:
        if k == "compile_instrs":
            continue
        elif len(os.path.splitext(k)[1]) == 0:
            ls.append(shorten(k))
    return ls

# This is the main function that takes the query as input and calls the function
# "execute_query" in file "query_run.py" where all processing is done and final
# output is returned here
def get_response_single_query(query):
    start_time = time.time()
    queryObj = QueryConversion(all_store_file, all_files, all_name_tokens_dic, all_comment_tokens_dict, program_domain_dict, tf_idf_name_tokens, tf_idf_symbol)
    ans = queryObj.execute_query(graph, TTLfile, RegexFile, query)
    end_time = time.time()
    if TIME:
        print("Time taken: ", end_time-start_time)
    return ans

# This is the main function that takes the query file as input and calls the
# function "execute_query_file" in file "query_run.py" where all processing is
# done and final output is returned here.
def get_response_query_file(filename):
    start_time = time.time()
    queryObj = QueryConversion(all_store_file, all_files, all_name_tokens_dict,\
    all_comment_tokens_dict, program_domain_dict, tf_idf_name_tokens, tf_idf_symbol)
    ans = queryObj.execute_query_file(graph, TTLfile, RegexFile, filename)
    end_time = time.time()
    if TIME:
        print("Time taken",+end_time-start_time)
    return ans

@app.route('/', methods=['GET'])
def index():
    title = 'Create the input'
    return render_template('layouts/index.html',
                           title=title)

@app.route('/querydev', methods=['GET', 'POST'])
def query_dev():
    title = 'Query SmartKT'
    if request.method == "POST":
        query = request.form.get('qry')
        file = request.files.get('file')
        if DEBUG:
            print(query, file)
        if query:
            resp = get_response_single_query(query)
        else:
            filename = secure_filename(file.filename)
            file.save(filename)
            resp = get_response_query_file(filename)
        return render_template('layouts/query_dev.html', resp=resp)
    return render_template('layouts/query_dev.html', title=title)

@app.route('/dependency', methods=['GET'])
def results():
    title = 'Result'
    d = pickle.load(open('data/dependencies.p', 'rb'))
    return render_template('layouts/results.html',
                           title=title, dep = d)

@app.route('/dependencydev', methods=['GET'])
def dependency_dev():
    create_dep_map()
    execs = getExecutables()
    data = visDOT('templates/static/images/dep.dot')
    # addDOT('templates/layouts/dependency_dev.html', 39, 16, data)
    title = "Dependency Map"
    return render_template('layouts/dependency_dev.html', data=json.dumps(data), title=title, execs=json.dumps(execs))

@app.route('/externdev', methods=['GET'])
def extern_dev():
    ls = []
    croot = ET.parse("data/final_static.xml").getroot()
    create_extern_link(ls, croot)
    symbols = list(set([x[0] for x in ls]))
    create_dep_map(ls, False)
    to_dot(ls, "templates/static/images/extern")
    data = visDOT("templates/static/images/extern.dot")
    title = "Extern Linkage"
    return render_template('layouts/extern_dev.html', title=title,
    data=data, symbols=symbols)

@app.route('/classmapdev', methods=['GET'])
def classmap_dev():
    croot = ET.parse("data/final_static.xml").getroot()
    structclassmap(croot)
    data = visDOT("templates/static/images/classmap.dot")
    title = "Class & Struct"
    return render_template('layouts/classmap_dev.html', title=title, data=json.dumps(data))

@app.route('/cfgdev', methods=['GET'])
def cfg_dev():
    os.system("python3 aggregrate.py")
    data = visDOT("templates/static/images/cfg.dot")
    title = "Control Flow"
    funcList, block2coverage, block2labels = pickle.load(open("templates/static/images/cfg.pkl", "rb"))
    return render_template('layouts/cfg_dev.html', title=title, data=json.dumps(data),
    funcList=json.dumps(funcList), block2coverage=json.dumps(block2coverage),
    block2labels=json.dumps(block2labels))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
