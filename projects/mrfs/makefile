a.out: main.cpp filesys.o libfsys.a
	g++ main.cpp filesys.o libfsys.a 
filesys.o: filesys.cpp
	g++ -c filesys.cpp
libfsys.a: fs.o in.o sb.o structures.h
	ar -cvq libfsys.a fs.o in.o sb.o
fs.o: fs.cpp structures.h
	g++ -c fs.cpp
in.o: in.cpp structures.h
	g++ -c in.cpp
sb.o: sb.cpp structures.h
	g++ -c sb.cpp

clean:
	rm a.out *.a *.o