import rdflib, sys, pickle
from rdflib import Graph, Literal, BNode, Namespace, RDF, URIRef
from rdflib.namespace import XSD
from collections import defaultdict

g = rdflib.Graph()

#Defining the prefixes
symbol = Namespace("http://smartKT/ns/symbol#")
prop = Namespace("http://smartKT/ns/properties#")

g.bind("symbol",symbol)
g.bind("prop",prop)

# Load the TTL file
TTLfile = sys.argv[1]
g.load(TTLfile, format='turtle')

queryTest = """
		PREFIX prop: <http://smartKT/ns/properties#>
		PREFIX symbol: <http://smartKT/ns/symbol#>

		SELECT ?file (COUNT(DISTINCT ?token) AS ?count)
		WHERE
		{
			{
				?id prop:spelling ?token;
					prop:is_defined_file ?file;

			}
			UNION
			{
				?id prop:spelling ?token;
					prop:is_called_file ?file;
			}
			UNION
			{
				?id prop:spelling ?token;
					prop:is_extern_file ?file;
			}
		}
		GROUP BY ?file
		"""

qresult = g.query(queryTest)

file_token_count = dict()

# Check if the query fetches some results or not
if(len(qresult)==0):
	print("No record found")

else:
	for st in qresult:
		file_token_count[st['file']] = st['count']

pickle.dump( file_token_count, open( sys.argv[2], "wb" ) )


#python execution cmd : python file_token_count.py ../../TTL\ files/libpng\ TTL/final_static.ttl
