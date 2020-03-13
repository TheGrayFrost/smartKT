#include <cstdio>
#include <pthread.h>
#include <unistd.h>
#include <string.h>
#include <errno.h>

// globals
pthread_t tid[2];
int counter = 0;

// external declarations
void * trythis(void * arg);
extern pthread_mutex_t lock;

int main()
{
    int i = 0;
    int error;

    int a[2];
  
    if (pthread_mutex_init(&lock, NULL) != 0) { 
        printf("\n mutex init has failed\n"); 
        return 1; 
    }

    while (i < 2)
    {
        a[i] = 2 * i;
        error = pthread_create(&(tid[i]), NULL, &trythis, (void *)(&a[i]));
        if (error != 0)
            printf("\nThread can't be created : [%s]", strerror(error));
        i++;
    }

    pthread_join(tid[0], NULL);
    pthread_join(tid[1], NULL);
    pthread_mutex_destroy(&lock); 
    return 0;
}
