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
		int x;
		A() {x = 0;}

};

namespace Foo
{
	int Bar::f(A v)
	{
		return v.x;
	}
}


using namespace Foo;


int main()
{
	A i;
	int x, y = Bar::f(i);
	return 0;
}