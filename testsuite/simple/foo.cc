#include <iostream>

extern int z;

int foo()
{
	int x;
	std::cout << "Inside foo's foo()\n";
	std::cout << "Seeing z = " << z << "\n";
	return z;
}