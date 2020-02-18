#define __csaved __cplusplus
#undef __cplusplus
#include "foo.hh"
#define __cplusplus __csaved
#include <stdio.h>

extern int y;

int main()
{
	int z = f();
	printf("z = %d, y = %d", z, y);
	return 0;
}