#include <iostream>

extern int z;

int foo()
{
	int x = 8;
	std::cout << "Inside foo's foo()\n";
	std::cout << "Seeing z = " << z << "\n";
	return z;
}