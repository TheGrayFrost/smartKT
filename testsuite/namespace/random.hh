#ifndef __RANDOM
#define __RANDOM

namespace Foo
{
	class A;
	namespace Bar
	{
		int f(A u);
	}
}

class Foo::A
{
	public:
		int x, y;
		A() {x = 0;}

};

#endif