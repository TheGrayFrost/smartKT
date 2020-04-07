//
// Created by Vishesh Agarwal on 19/03/18.
//

#include "structures.h"
#include <signal.h>
#include <unistd.h>

#define NAMELEN 30
#define INLEN 2
#define TOTLEN (NAMELEN + INLEN)

void us2char (char * d, unsigned short r)
{
    for (int i = 0; i < 2; ++i)
        *(d + i) = ((char *) &r)[i];
}

void int2char (char * d, int r)
{
    for (int i = 0; i < 4; ++i)
        *(d + i) = ((char *) &r)[i];
}

void progress_bar (double progress)
{
    int barWidth = 70;
    cout << "[";
    int pos = barWidth * progress;
    for (int i = 0; i <= barWidth; ++i)
    {
        if (i < pos) cout << "=";
        else if (i == pos) cout << ">";
        else cout << " ";
    }
    cout << "] " << int(progress * 100.0) << " %\r";
    cout.flush();
}


fsys::fsys(int s)
{
    superbl = new sb(s);
    cout << "Superblock created.\n";
    cout << "Inode list created.\n";
    dblist = new char [superbl->maxdb][DBSIZE];
    cout << "Data block list created.\n";
    for (int i = 0; i < PTSIZE; ++i)
        ptable[i][0] = ptable[i][1] = -1;
    cout << "Process table created.\n";
    createdir();
    cout << "Root initiated.\n";
}

//creates a new directory in pwd
//. and .. are added autmatically
//inno of created directory is returned
//the inode returned is fresh and clear
int fsys::createdir()
{
    unsigned short inno = superbl->getinode();
    int dbno = superbl->getblock();
    int loc = 0;

    snprintf(&dblist[dbno][loc], NAMELEN + 1, "%s", ".");
    loc += NAMELEN;
    us2char(&dblist[dbno][loc], inno);
    loc += INLEN;
    snprintf(&dblist[dbno][loc], NAMELEN + 1, "%s", "..");
    loc += NAMELEN;
    us2char(&dblist[dbno][loc], getpwd());
    loc += INLEN;

    inlist[inno].ftype = true;
    inlist[inno].fsize = loc;
    inlist[inno].lastmod = inlist[inno].lastrd = time(NULL);
    inlist[inno].accp = 0777;
    inlist[inno].dirbl[0] = dbno;

    return inno;
}

//adds a new datablock onto an inode
//sets the accounting information accordingly
//returns pointer to start of added block
char * fsys::addblock (in& ap)
{

    int rx = DBSIZE / sizeof(int);
    int dbno = superbl->getblock();
    int bno = ap.fsize / DBSIZE, spill, newman;
    bno += (ap.fsize % DBSIZE ? 1 : 0);
    if (bno < INDB)
        ap.dirbl[bno] = dbno;
    else
    {
        bno -= INDB;
        if (bno == 0)
            ap.sindbl = superbl->getblock();
        if (bno < rx)
            int2char((char *)&((int *)dblist[ap.sindbl])[bno], dbno);
        else
        {
            bno -= rx;
            if (bno == 0)
                ap.dindbl = superbl->getblock();
            spill = bno % rx;
            bno /= rx;
            if (spill == 0)
            {
                newman = superbl->getblock();
                int2char((char *)&((int *)dblist[ap.dindbl])[bno], newman);
            }
            int2char((char *)&((int *)dblist[((int *)dblist[ap.dindbl])[bno]])[spill], dbno);
        }
    }
    return dblist[dbno];
}

// adds entry nm of type ty in pwd
// will need to add a parser here later
// returns inno of added entry
//the inode returned is fresh and clear
int fsys::addentry (char * nm, bool ty)
{
    char * u = NULL;
    in * r = &inlist[getpwd()];
    int bno = r->fsize / DBSIZE, spused = r->fsize % DBSIZE;
    bno -= (spused ? 0 : 1);
    spused = (spused ? spused : DBSIZE);
    int inno;
    if (spused == DBSIZE)
        u = addblock(inlist[getpwd()]);
    else
        u = &dblist[getinblock(bno, r)][spused];
    snprintf(u, NAMELEN + 1, "%s", nm);
    u += NAMELEN;

    if (ty)
        inno = createdir();
    else
        inno = superbl->getinode();
    us2char(u, inno);

    if (!ty)
        inlist[inno].clear();

    inlist[getpwd()].fsize += TOTLEN;
    inlist[getpwd()].lastmod = time(NULL);

    return inno;
}

//returns int address of block bno of inode up in dblist
int fsys::getinblock (int bno, in * up)
{
    int spill = up->fsize / DBSIZE;
    spill -= (up->fsize % DBSIZE ? 0 : 1);
    if (bno > spill)
    {
        cout << "\nError: Bad access. You're getting too ahead of yourself.\n\n";
        return -1;
    }
    int rx = DBSIZE / sizeof(int);
    if (bno < INDB)
        return up->dirbl[bno];
    else
    {
        bno -= INDB;
        if (bno < rx)
            return ((int *)dblist[up->sindbl])[bno];
        else
        {
            bno -= rx;
            spill = bno % rx;
            bno /= rx;
            return ((int *)dblist[((int *)dblist[up->dindbl])[bno]])[spill];
        }
    }
}

// returns inode corresponding to file fn in pwd
// it deletes the corresponding directory entry if del is set to true
// if the file is a directory, then it's entry is deleted only if force is set to true
// del and force are false by default
unsigned short fsys::locate (char * fn, bool del, bool force)
{
    in * up = &inlist[getpwd()];
    int ent = up->fsize / DBSIZE, lno = up->fsize % DBSIZE, enno = DBSIZE/TOTLEN, loc;
    ent -= (lno ? 0 : 1);
    lno = (lno ? lno : DBSIZE);
    lno /= TOTLEN;
    unsigned short inno = -1;
    char * search, name[NAMELEN+1], * replacer;

    for (int bno = 0; bno <= ent; ++bno)
    {
        loc = getinblock(bno, up);
        if (loc == -1)
            return inno;
        search = dblist[loc];
        if (bno == ent)
            enno = lno;
        for (int i = 0; i < enno; ++i)
        {
            snprintf(name, NAMELEN+1, "%s", search);
            if (strcmp(name, fn) == 0)
            {
                inno = *((unsigned short *)(search + NAMELEN));
                if (del)    //if we have to delete entry
                {
                    if ((inlist[inno].ftype) && !force) //if the entry turns out to be a directory and force is false
                        return -2;
                    lno--;  //preparations for replacement with the last entry
                    if ((bno != ent) || (i != lno))    //if not deleting the last entry -> need a replacement
                    {
                        replacer = dblist[getinblock(ent, up)] + lno * TOTLEN;
                        snprintf (search, NAMELEN + 1, "%s", replacer);
                        us2char (search + NAMELEN, *(unsigned short *)(replacer + NAMELEN));
                    }
                    if (lno == 0)   //free the last block if there was only one entry on it
                        superbl->freeblock(ent);
                    up->fsize -= TOTLEN;
                    up->lastmod = time(NULL);
                }
                return inno;
            }
            search += TOTLEN;
        }
    }
    return inno;
}

//returns pwd corresponding to current process
int fsys::getpwd()
{
    int find = getpid(), i;

    for (i = 0; (i < PTSIZE) && (ptable[i][0] != -1); ++i)  //look for already present people
        if (ptable[i][0] == find)
            return ptable[i][1];

    //i holds number of entries in table
    //let us kill all dead entries
    --i;
    for (int j = 0; (j < PTSIZE) && (ptable[j][0] != -1); ++j)
    {
        if (kill(ptable[j][0], 0) == -1) //this process has died -> replace with last entry
        {
            ptable[j][0] = ptable[i][0];
            ptable[j][1] = ptable[i][1];
            ptable[i][0] = -1;
            i--;
        }
    }
    i++;    //make i once again hold the number of entries

    if (i == PTSIZE)
    {
        cout << "Process access limit reached.\nAll operations for the current process are halted.\n\n";
        return -1;
    }

    int fpar = getppid(), parpw = 0;
    for (int j = 0; (j < PTSIZE) && (ptable[j][0] != -1); ++j)
    {
        if (ptable[j][0] == fpar)
        {
            parpw = ptable[i][1];
            break;
        }
    }
    ptable[i][0] = find;
    ptable[i][1] = parpw;
    return parpw;
}

//changes pwd corresponding to current process
void fsys::chpwd(int newpwd)
{
    int find = getpid();

    for (int i = 0; (i < PTSIZE) && (ptable[i][0] != -1); ++i)
        if (ptable[i][0] == find)
            ptable[i][1] = newpwd;
}


