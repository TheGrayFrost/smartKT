int bar();
int myrand();

extern int z;

int z = 0;

int main()
{
	static int x = z + myrand();
	int y = bar();
	return 0;
}