#include "random.hh"

namespace Foo
{
	extern int u, v;
}

using namespace Foo;
using namespace Bar;

int r = v, z = u;

int main()
{
	A i, j;
	int x = z = f(j), y = Bar::f(i);
	return 0;
}