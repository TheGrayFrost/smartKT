# Usage
# python3 name_token_file_count.py <name_tokens.p> <final_static.ttl> <output_token_file_count.p>

import rdflib, sys, pickle
from rdflib import Graph, Literal, BNode, Namespace, RDF, URIRef
from rdflib.namespace import XSD
from collections import defaultdict
import re, sys
from importlib import reload as reload

reload(sys)

g = rdflib.Graph()

pickle_file = sys.argv[1]
all_name_tokens = pickle.load( open( pickle_file, "rb" ) )
token_file_count = dict()

#Defining the prefixes
symbol = Namespace("http://smartKT/ns/symbol#")
prop = Namespace("http://smartKT/ns/properties#")

g.bind("symbol",symbol)
g.bind("prop",prop)

# Load the TTL file
TTLfile = sys.argv[2]
g.load(TTLfile, format='turtle')

for token in all_name_tokens:
	token = re.sub(r"[,.;@#?*!&$'\"\"\\]+\ *", "", token)
	print(token)

	#ek file mai id kitni baar aya hai
	queryTest = """
			PREFIX prop: <http://smartKT/ns/properties#>
			PREFIX symbol: <http://smartKT/ns/symbol#>

			SELECT ?file (COUNT(*) AS ?count)
			WHERE
			{
				{
					?id prop:name_token "%s";
						prop:is_defined_file ?file;

				}
				UNION
				{
					?id prop:name_token "%s";
						prop:is_called_file ?file;
				}
				UNION
				{
					?id prop:name_token "%s";
						prop:is_extern_file ?file;
				}
			}
			GROUP BY ?file
			"""

	queryTest = queryTest % (token,token,token)

	qresult = g.query(queryTest)

	file_token_count = dict()

	# Check if the query fetches some results or not
	if(len(qresult)==0):
		print("No record found")

	else:
		#print "\nResult: "
		token_file_count[token] = dict()

		for st in qresult:
			token_file_count[token][st['file']] = st['count']

	print(len(token_file_count[token].keys()))


pickle.dump( token_file_count, open( sys.argv[3], "wb" ) )
