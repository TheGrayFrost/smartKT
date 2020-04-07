//
// Created by Vishesh Agarwal on 19/03/18.
//

#include "structures.h"

in::in()
{
    ftype = false;
    fsize = 0;
    lastmod = lastrd = time(NULL);
    accp = 0777;
    for (int i = 0; i < INDB; ++i)
        dirbl[i] = -1;
    sindbl = -1;
}

void in::clear()
{
    ftype = false;
    fsize = 0;
    lastmod = lastrd = time(NULL);
    accp = 0777;
    for (int i = 0; i < INDB; ++i)
        dirbl[i] = -1;
    sindbl = -1;
    dindbl = -1;
}

void in::display()
{
    char name[47];
    if(ftype)
        name[0] = 'd';
    else
        name[0] = '-';
    char g[] = {'x', 'w', 'r'};
    int ext = accp, k = 9;
    for (int i = 0; i < 3; ++i)
    {
        for (int j = 0; j < 3; ++j)
        {
            if (ext & 1)
                name[k--] = g[j];
            else
                name[k--] = '-';
            ext >>= 1;
        }
    }
    sprintf (&name[10], " %10d ", fsize);
    string u = ctime_r(&lastmod, &name[22]);
    name[46] = ' ';
    cout << name;
    cout.flush();
}

void in::dump (ofstream& fp)
{
    fp.write((char *)&ftype, sizeof(bool));
    fp.write((char *)&fsize, sizeof(int));
    fp.write((char *)&lastmod, sizeof(time_t));
    fp.write((char *)&lastrd, sizeof(time_t));
    fp.write((char *)&accp, sizeof(int));
    fp.write((char *)dirbl, INDB * sizeof(int));
    fp.write((char *)&sindbl, sizeof(int));
    fp.write((char *)&dindbl, sizeof(int));
}

void in::restore(ifstream& fp)
{
    fp.read((char *)&ftype, sizeof(bool));
    fp.read((char *)&fsize, sizeof(int));
    fp.read((char *)&lastmod, sizeof(time_t));
    fp.read((char *)&lastrd, sizeof(time_t));
    fp.read((char *)&accp, sizeof(int));
    fp.read((char *)dirbl, INDB * sizeof(int));
    fp.read((char *)&sindbl, sizeof(int));
    fp.read((char *)&dindbl, sizeof(int));
}