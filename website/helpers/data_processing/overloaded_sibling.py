import rdflib, sys
from rdflib import Graph, Literal, BNode, Namespace, RDF, URIRef
from rdflib.namespace import XSD
from collections import defaultdict

g = rdflib.Graph()

g1 = Graph()

#Defining the prefixes
symbol = Namespace("http://smartKT/ns/symbol#")
prop = Namespace("http://smartKT/ns/properties#")

g1.bind("symbol",symbol)
g1.bind("prop",prop)

# Load the TTL file
TTLfile = sys.argv[1]
g.load(TTLfile, format='turtle')

res = list()

#inner query formed overloaded groups and outer query selects all the usr's matching the overloaded groups
#overloaded functions shld be in the same scope so matching with the lex_parent_usr which will be same for overloaded functions

queryTest = """
		PREFIX prop: <http://smartKT/ns/properties#>
		PREFIX symbol: <http://smartKT/ns/symbol#>

		SELECT ?fname ?type ?pid ?id_n
		WHERE
		{
			?id prop:lex_parent_id ?pid ;
			     prop:has_id ?id_n ;
			     prop:spelling ?fname ;
		     	 prop:return_type ?type ;
		     	 prop:absolute_file_path ?file .

			{
				SELECT ?fname ?type ?file ?pid
				WHERE
				{
				    ?func prop:spelling ?fname ;
				     	  prop:return_type ?type ;
				     	  prop:absolute_file_path ?file ;
				     	  prop:lex_parent_id ?pid .
				}
				GROUP BY ?fname ?type ?file ?pid
				HAVING (COUNT(*) > 1)
			}
		}
		"""

qresult = g.query(queryTest)

overload = defaultdict(set)

# Check if the query fetches some results or not
if(len(qresult)==0):
	print("No record found")

else:
	#print "\nResult: "
	for st in qresult:
		overload[st['fname']+'#'+st['type']+'#'+st['pid']].add(st['id_n'].split('#')[0])

for key in overload:
	for i,x in enumerate(overload[key]):
		for j,y in enumerate(overload[key]):
			if i!=j:
				g1.add((symbol[x], prop['overloaded_sibling'], symbol[y]))


g1.serialize(sys.argv[2],format='ttl')
