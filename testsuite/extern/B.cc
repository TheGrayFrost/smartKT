#include <iostream>

int f();

class A
{
	public:
		int r;
		A();
};

A::A() {std::cout << "In class A's cons.\n"; r = f();}

A v, * p;