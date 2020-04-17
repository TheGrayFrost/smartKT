#include <iostream>
#include "foo.hpp"

unsigned long int p[][3] = {{1, 2, 3}, {4, 5, 6}};

int main()
{
	A::m = 31;
	A * u = f(v);
	std::cout << "u->r = " << u->r << "\n";
	return 0;
}
