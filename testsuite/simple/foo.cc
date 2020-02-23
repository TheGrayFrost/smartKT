#include <iostream>

extern int z;

int foo()
{
	std::cout << "Inside foo's foo()\n";
	return z;
}