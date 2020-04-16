#include <iostream>

static int y;
int z = 4;

int foo();

int bar()
{
	std::cout << "Inside bar's bar()\n";
	int z = 7;
	z += foo();
	return z;
}