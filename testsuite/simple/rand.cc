#include <iostream>

static int z = 3;

int foo()
{
	std::cout << "Inside rand's foo()\n";
	return z;
}