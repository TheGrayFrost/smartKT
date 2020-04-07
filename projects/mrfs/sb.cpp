//
// Created by Vishesh Agarwal on 19/03/18.
//

#include "structures.h"


sem_t sem1, sem2;

sb::sb (int s)
{
    size = s * 1024 * 1024;
    maxin = MAXINODE;
    inused = 0;
    maxdb = size / DBSIZE;
    dbused = 0;
    for (int i = 0; i < maxin; ++i)
        inbmap[i] = false;
    if (s == 0)
        dbbmap = NULL;
    else
    {
        dbbmap = new bool [maxdb];
        for (int i = 0; i < maxdb; ++i)
            dbbmap[i] = false;
    }
}

int sb::getblock()
{
    if (dbused == maxdb)
        return -1;
    for (int i = 0; i < maxdb; ++i)
    {
        if (dbbmap[i] == false)
        {
            dbbmap[i] = true;
            dbused++;
            return i;
        }
    }
    return -1;
}

int sb::getinode()
{
    if (inused == maxin)
        return -1;
    for (int i = 0; i < maxin; ++i)
    {
        if (inbmap[i] == false)
        {
            inbmap[i] = true;
            inused++;
            return i;
        }
    }
    return -1;
}

void sb::freeblock(int ad)
{
    dbbmap[ad] = false;
    dbused--;
}

void sb::freeinode(int ad)
{
    inbmap[ad] = false;
    inused--;
}

void sb::dump (ofstream& fp)
{
    fp.write((char *)&size, sizeof(int));
    fp.write((char *)&maxin, sizeof(int));
    fp.write((char *)&inused, sizeof(int));
    fp.write((char *)&maxdb, sizeof(int));
    fp.write((char *)&dbused, sizeof(int));
    fp.write((char *)inbmap, MAXINODE * sizeof(bool));
    fp.write((char *)dbbmap, maxdb * sizeof(bool));
}

void sb::restore(ifstream& fp)
{
    fp.read((char *)&size, sizeof(int));
    fp.read((char *)&maxin, sizeof(int));
    fp.read((char *)&inused, sizeof(int));
    fp.read((char *)&maxdb, sizeof(int));
    fp.read((char *)&dbused, sizeof(int));
    fp.read((char *)inbmap, MAXINODE * sizeof(bool));
    fp.read((char *)dbbmap, maxdb * sizeof(bool));
}

void sb::print ()
{
    cout << "File system size: " << size << " bytes.\n";
    cout << "Total data usage: " << dbused * DBSIZE << " bytes.\n";
    cout << "Max files allowed: " << maxin << "\n";
    cout << "Total files in system: " << inused << "\n\n";
}