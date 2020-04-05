#include <iostream>

int f();

// Class A's defination
class A
{
	public:
		int r;
		A();
};

A::A() {std::cout << "In class A's cons.\n"; r = f();}

// Instantiation of p
A v, * p;
