#include <iostream>
#include "foo.hh"

using namespace A::B;

int main()
{
	std::cout << A::x << "\n";
	A::x = f();
	std::cout << A::x << "\n";
	return 0;
}