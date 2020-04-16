#ifndef __FOO
#define __FOO

class A
{
	public:
		int r;
		static int m;
		int p[2];
		A();
};

extern A v;

A * f(A& x);

void ref()
{
	int p;
	static int i;
}

#endif