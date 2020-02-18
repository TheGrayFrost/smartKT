int foo();
int bar();
extern int z;

int main()
{
	static int x = z + foo();
	int y = bar();
	return 0;
}