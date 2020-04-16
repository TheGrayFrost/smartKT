#include "foo.h"

A v, * p;

A * f(A * x)
{
	p = x;
	return p;
}
