/*Class A's defination will be provided by someone else*/
class A;

// Externally linked p
extern A * p;

A * f(A& x)
{
	p = &x;
	return p;
}
