CXX=g++
CXXFLAGS=-std=c++14

LIBS=-lclang

all: ast2xml calls # funcs

ast2xml: ast2xml.cc
	$(CXX) $(CXXFLAGS) `xml2-config --cflags --libs` -lclang $(CFLAGS) -o $@ $^

# funcs: functions.cc
# 	$(CXX) $(CXXFLAGS) -lclang -o $@ $^

calls: calls.cc
	$(CXX) $(CXXFLAGS) -lclang -o $@ $^

clean :
	- rm -f calls ast2xml # funcs
