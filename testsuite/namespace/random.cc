#include "random.hh"

namespace Foo
{
	int u, v;
	namespace Bar
	{
		int f (A z);
		static int f();
	}
	static int Bar::f()
	{
		static int p = 7;
		{
			int p = 9;
		}
		return p;
	}
}

int Foo::Bar::f(A v)
{
	int a, b = Foo::Bar::f();
	return v.x;
}