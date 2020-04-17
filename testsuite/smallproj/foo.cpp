#include "foo.hpp"

A::A() {r = 7;}
int A::m = 9;

A v, * p;

A * f(A& x)
{
	p = &x;
	return p;
}
