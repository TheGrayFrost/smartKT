#include <iostream>

typedef int myint;
extern myint x;

myint f()
{
	std::cout << "In f():\n";
	return x;
}

myint f(myint u)
{
	std::cout << "In f(myint):\n";
	return u;
}

namespace Foo
{
	class A
	{
		public:
			int r;
			A();
	};
	namespace Bar {extern A v;}
}

int main()
{
	std::cout << Foo::Bar::v.r << "\n";
	return 0;
}