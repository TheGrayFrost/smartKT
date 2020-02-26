#include <iostream>

static int x = 9;

int f()
{
	std::cout << "In f():\n";
	return x;
}

A * f(A& x);

class A
{
	public:
		int r;
		A();
};

extern A v;

int main()
{
	A * u = f(v);
	std::cout << "Value of u->r = " << u->r << "\n";
	return 0;
}