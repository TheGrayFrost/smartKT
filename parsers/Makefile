CXX=g++
CXXFLAGS=-std=c++14 `xml2-config --cflags`

LIBS=`xml2-config --libs` -lclang

all: ast2xml calls # funcs

ast2xml: ast2xml.cc
	$(CXX) $(CXXFLAGS) -o $@ $^ $(LIBS)

# funcs: functions.cc
# 	$(CXX) $(CXXFLAGS) -lclang -o $@ $^

# added `-static-libstdc++` as it was giving error:
# parsers/calls: /usr/lib64/libstdc++.so.6: version `GLIBCXX_3.4.21' not found (required by parsers/calls)
# on the server
calls: calls.cc
	$(CXX) $(CXXFLAGS) -static-libstdc++ -o $@ $^ $(LIBS)

clean :
	- rm -f calls ast2xml # funcs
