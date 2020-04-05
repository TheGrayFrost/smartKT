#include <iostream>

static int x = 9;

class A
{
	public:
		int r;
		A();
};


int f()
{
	std::cout << "In f():\n";
	return x;
}

A * f(A& x);

// extern linking
extern A v;

int main()
{
	A * u = f(v);
	std::cout << "Value of u->r = " << u->r << "\n";
	return 0;
}
