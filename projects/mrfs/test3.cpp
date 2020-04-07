#include "filesys.h"
#include <pthread.h>
#include <unistd.h>
#include <string>
#include <vector>
#include <algorithm>
#include <sstream>
#include <cassert>

using namespace std;

pthread_mutex_t mutex1 = PTHREAD_MUTEX_INITIALIZER;
string mydocs = "mydocs", mytext = "mytext", mypapers = "mypapers", mycode = "mycode", test = "test";

void *thread1_running (void *)
{
    pthread_mutex_lock(&mutex1);
    char *A2Z = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
    chdir_myfs("mydocs");
    chdir_myfs("mytext");
    int fd = open_myfs("test", 'w');
    write_myfs(fd, 26, A2Z);
    chdir_myfs("..");
    chdir_myfs("..");
    pthread_mutex_unlock(&mutex1);
    return NULL;
}

void *thread2_running (void * fn)
{
    pthread_mutex_lock(&mutex1);
    chdir_myfs("mycode");
    copy_pc2myfs((char *)(fn), "newtest");
    chdir_myfs("..");
    pthread_mutex_unlock(&mutex1);
    return NULL;
}

int main(int argc, char * argv[])
{
	//Test 3
	pthread_t thread1, thread2;

	create_myfs(10);
	mkdir_myfs((char *) mydocs.c_str());
	mkdir_myfs((char *) mycode.c_str());
	chdir_myfs((char *) mydocs.c_str());
	mkdir_myfs((char *) mytext.c_str());
	mkdir_myfs((char *) mypapers.c_str());
	chdir_myfs((char *) "..");
	ls_myfs();
	chdir_myfs((char *) mydocs.c_str());
	ls_myfs();
	chdir_myfs("..");
	ls_myfs();

	pthread_create(&thread1, NULL, thread1_running, NULL);
	pthread_create(&thread2, NULL, thread2_running, (void *)(argv[1]));

	pthread_join(thread1, NULL);
	pthread_join(thread2, NULL);

	ls_myfs();
	chdir_myfs("mydocs");
	chdir_myfs("mytext");
	showfile_myfs("test");
	ls_myfs();
	chdir_myfs("..");
	chdir_myfs("..");
	chdir_myfs("mycode");
	showfile_myfs("newtest");

    return 0;
}