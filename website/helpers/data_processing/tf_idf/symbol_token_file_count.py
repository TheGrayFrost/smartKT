import rdflib, sys, pickle, re
from rdflib import Graph, Literal, BNode, Namespace, RDF, URIRef
from rdflib.namespace import XSD
from collections import defaultdict
from importlib import reload as reload

reload(sys)

g = rdflib.Graph()

pickle_file = sys.argv[1]
all_store = pickle.load( open( pickle_file, "rb" ) )

all_symbol = all_store['symbol'].keys()

token_file_count = dict()

#Defining the prefixes
symbol = Namespace("http://smartKT/ns/symbol#")
prop = Namespace("http://smartKT/ns/properties#")

g.bind("symbol",symbol)
g.bind("prop",prop)

# Load the TTL file
TTLfile = sys.argv[2]
g.load(TTLfile, format='turtle')

for token in all_symbol:

	#ek file mai id kitni baar aya hai
	queryTest = """
			PREFIX prop: <http://smartKT/ns/properties#>
			PREFIX symbol: <http://smartKT/ns/symbol#>

			SELECT ?file (COUNT(*) AS ?count)
			WHERE
			{
				{
					?id prop:spelling "%s";
						prop:is_defined_file ?file;

				}
				UNION
				{
					?id prop:spelling "%s";
						prop:is_called_file ?file;
				}
				UNION
				{
					?id prop:spelling "%s";
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
		
		token_file_count[token] = dict()

		for st in qresult:
			token_file_count[token][st['file']] = st['count']


pickle.dump( token_file_count, open( sys.argv[3], "wb" ) )
