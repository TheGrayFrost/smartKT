#include <iostream>
#include "foo.hh"

using namespace A::B;

int main()
{
	int y = 9;
	std::cout << A::x << "\n";
	A::x = f();
	std::cout << A::x << "\n";
	return 0;
}