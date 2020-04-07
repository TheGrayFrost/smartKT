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

int main(int argc, char * argv[])
{
    assert(create_myfs(10) >= 0);

    // Test 2
    assert(restore_myfs(argv[1]) >= 0);
    assert(ls_myfs() >= 0);

    int fd = open_myfs("mytest.txt", 'r');
    string tmp;
    char buff[1024];

    vector<int> vec;
    while(!eof_myfs(fd))
    {
        int nbytes = read_myfs(fd, 1024, buff);
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
    int fd2 = open_myfs("sorted.txt", 'w');
    for (auto j : vec) 
    {
        tmp = to_string(j) + "\n";
        write_myfs(fd2, strlen((char *)tmp.c_str()), (char *)tmp.c_str());
    }

    close_myfs(fd2);
    assert(ls_myfs() >= 0);
    assert(showfile_myfs("sorted.txt") >= 0);

    return 0;
}