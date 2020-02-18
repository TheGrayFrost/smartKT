static int y;
int z = 4;

int foo1();

int bar()
{
	int z = 7;
	z += foo1();
	return z;
}