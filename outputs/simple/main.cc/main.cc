int b[4];

struct r
{
	int x;
	char y;
} z;

int main()
{
	int a[2] = {1, 4};
	r s[4];
	r k = z;
	a[1] = 9;
	int x = 8;
	int * p;
	p = &x;
	(*p) = 5;
	p = &b[2];
	(*p) = 7;
	p = a;
	p = &s[2].x;
	p = (int *)&k.y;
	int * q = p;
	q++;
	q = p + 1;
	return 0;
}