#include <iostream>

typedef int myint;
extern myint f();

namespace Foo
{
	class A
	{
		public:
			int r;
			A();
	};
	A::A() {std::cout << "In class A's cons.\n"; r = f();}
	A v;
	namespace Bar {A v;}
}
