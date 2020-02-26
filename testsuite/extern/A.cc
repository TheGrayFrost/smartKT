class A;

extern A * p;

A * f(A& x)
{
	p = &x;
	return p;
}