#include <iostream>

static int y;
int z = 2;

int foo();

int foo()
{
	int x, r;
	std::cout << "Inside bar's foo()\n";
	std::cout << "Seeing z = " << z << "\n";
	return z;
}

// checking how function calls show up
int bar()
{
	std::cout << "Inside bar's bar()\n";
	std::cout << "Seeing z = " << z << "\n";
	int z = 3;
	std::cout << "Seeing z = " << z << "\n";
	z += foo(); // this is a call to foo
	std::cout << "Seeing z = " << z << "\n";
	return z;
}