CXX=g++
CXXFLAGS=-std=c++14 `xml2-config --cflags`

LIBS=`xml2-config --libs` -lclang

all: ast2xml calls # funcs

ast2xml: ast2xml.cc
	$(CXX) $(CXXFLAGS) -o $@ $^ `xml2-config --cflags --libs` -lclang

# funcs: functions.cc
# 	$(CXX) $(CXXFLAGS) -lclang -o $@ $^

calls: calls.cc
	$(CXX) $(CXXFLAGS) -o $@ $^ $(LIBS)

clean :
	- rm -f calls ast2xml # funcs
