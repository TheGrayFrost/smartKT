#include<cstdio>
#include<cstdlib>
#include <pthread.h>

extern int counter;
pthread_mutex_t lock; 

void * trythis(void * arg)
{
	printf("\n Came here with arg = %d\n", *((int *)arg));
    unsigned long i = 0, r = 1;
    pthread_mutex_lock(&lock);
    counter += r;
    printf("\n Job %d has started\n", counter);
    for (i = 0; i < 10; i++);
    printf("\n Job %d has finished\n", counter);
    pthread_mutex_unlock(&lock); 
    return NULL;
}