#This code merges the ttl files and creates a single ttl file.

from rdflib import Graph
import sys
import argparse

parser = argparse.ArgumentParser(description='Files needed to run the code.')
parser.add_argument(dest='static_file', action='store', help='Input the Static TTL file path')
parser.add_argument(dest='dynamic_file', action='store', help='Input the Dynamic TTL file path')
parser.add_argument(dest='comment_file', action='store', help='Input the Comment TTL file path')
parser.add_argument(dest='TTL_file', action='store', help='Resultant TTL file path')

args = vars(parser.parse_args())
static_file = args['static_file']
dynamic_file = args['dynamic_file']
comment_file = args['comment_file']
TTL_file = args['TTL_file']

graph = Graph()

graph.parse(static_file,format="ttl")
if dynamic_file != "NONE":
    graph.parse(dynamic_file,format="ttl")

if comment_file != "NONE":
    graph.parse(comment_file,format="ttl")

graph.serialize(TTL_file,format="ttl")

#python merge.py ../../TTL\ files/libpng\ TTL/final_static.ttl ../../TTL\ files/libpng\ TTL/final_dynamic.ttl ../../TTL\ files/libpng\ TTL/final_comments.ttl ../../TTL\ files/libpng\ TTL/final.ttl

#python merge.py ../../TTL\ files/libpng\ TTL/final_dynamic_test.ttl ../../TTL\ files/libpng\ TTL/final_dynamic_bar.ttl ../../TTL\ files/libpng\ TTL/final_dynamic.ttl
