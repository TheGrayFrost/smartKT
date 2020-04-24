#include "foo.h"
#include <stdlib.h>

int main()
{
	A * u = f(&v);
	A * x = (A *)malloc(5 * sizeof(A));
	A * y = (A *)calloc(5, sizeof(A));
	A z[5];
	for (int i = 0; i < 5; ++i)
	{
		z[i].r++;
		x[i].r++;
		y[i].r++;
		x[i].r = 7;
	}
	free(x);
	free(y);
	return 0;
}
