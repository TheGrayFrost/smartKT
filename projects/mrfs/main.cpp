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

void *thread2_running (void *)
{
    pthread_mutex_lock(&mutex1);
    chdir_myfs("mycode");
    copy_pc2myfs("./test/test1.txt", "newtest");
    chdir_myfs("..");
    pthread_mutex_unlock(&mutex1);
    return NULL;
}

int main()
{
    assert(create_myfs(10) >= 0);
    
    // Test 1
    

    // for (int i = 1; i <= 12; i++)
    // {
    //     string fname = "./test/test_" + to_string(i) + ".cpp";
    //     string dname = "myfs_" + fname.substr(7);
    //     assert(copy_pc2myfs((char *)fname.c_str(),(char *)dname.c_str()) >= 0);
    // }

    // char del;
    // string tmp;

    // do
    // {
    //     assert(ls_myfs() >= 0);
    //     cout<<"\nEnter file to delete from the ones listed above : ";
    //     cin>> tmp;
    //     assert(rm_myfs((char*)tmp.c_str()) >= 0);
    //     cout << "\n\nWant to delete more files? (y/n): ";
    //     cin >> del;
    // } while (del == 'y');
    // assert(ls_myfs() >= 0);
    

    // Test 2
    int fd2, fd = open_myfs("mytest.txt", 'w');
    string tmp;
    for (int i = 0; i < 100; i++)
    {
        tmp = to_string(rand() % 1000) + "\n";
        write_myfs(fd, strlen((char *)tmp.c_str()), (char *)tmp.c_str());
    }
    assert(close_myfs(fd) >= 0);

    int N = 4, nbytes;
    char buff[1024];
    
    cout << "\nEnter number of copies to be made : ";
    // cin >> N;
    
    for (int i = 1; i <= N; i++)
    {
        fd = open_myfs("mytest.txt", 'r');
        fd2 = open_myfs((char *)("mytest-" + to_string(i) + ".txt").c_str(), 'w');
        while (eof_myfs(fd) != 1)
        {
            nbytes = read_myfs(fd, 1024, buff);
            write_myfs(fd2, nbytes, buff);
        }
        close_myfs(fd);
        close_myfs(fd2);
    }
    assert(ls_myfs() >= 0);
    assert(dump_myfs("./mydump-34.backup") == 0);


    // Test 3
    assert(restore_myfs("./mydump-34.backup") >= 0);
    assert(ls_myfs() >= 0);

    fd = open_myfs("mytest.txt", 'r');
    vector<int> vec;
    while(!eof_myfs(fd))
    {
        nbytes = read_myfs(fd, 1024, buff);
        if (nbytes)
        {
            stringstream ss(buff);
            while (getline(ss, tmp, '\n') && nbytes > 1)
            {
                vec.push_back(stoi(tmp));
                nbytes -= strlen((char *)tmp.c_str()) + 1;
            }
        }
    }
    sort(vec.begin(), vec.end());
    close_myfs(fd);
    fd2 = open_myfs("sorted.txt", 'w');
    for (auto j : vec) 
    {
        tmp = to_string(j) + "\n";
        write_myfs(fd2, strlen((char *)tmp.c_str()), (char *)tmp.c_str());
    }

    close_myfs(fd2);
    assert(ls_myfs() >= 0);
    assert(showfile_myfs("sorted.txt") >= 0);

	//Test 4
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
	pthread_create(&thread2, NULL, thread2_running, NULL);

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
