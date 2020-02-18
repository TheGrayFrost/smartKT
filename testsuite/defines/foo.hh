#ifndef __FOO__
#define __FOO__

#ifdef __cplusplus
extern "C"
{
	int f() {return 7;}
}
#else
int f() {return 5;}
#endif

#endif