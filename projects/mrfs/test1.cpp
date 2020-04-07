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

int main()
{
    assert(create_myfs(10) >= 0);

    // Test 1
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

    return 0;
}
