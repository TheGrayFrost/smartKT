#include <iostream>

static int z = 1;

int foo()
{
	int r = 2;
	std::cout << "Inside rand's foo()\n";
	std::cout << "Seeing z = " << z << "\n";
	return z;
}

int myrand()
{
	std::cout << "Inside rand's myrand()\n";
	std::cout << "Seeing z = " << z << "\n";
	return z;
}