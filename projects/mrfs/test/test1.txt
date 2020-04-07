//
// Created by Vishesh Agarwal on 19/03/18.
//

#include "structures.h"

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


fsys::fsys(int s)
{
    superbl = new sb(s);
    cout << "Superblock created.\n";
    cout << "Inode list created.\n";
    dblist = new char [superbl->maxdb][DBSIZE];
    cout << "Data block list created.\n";
    pwd = 0;
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
    us2char(&dblist[dbno][loc], pwd);
    loc += INLEN;

    inlist[inno].ftype = true;
    inlist[inno].fsize = loc;
    inlist[inno].spused = loc;
    inlist[inno].lastmod = inlist[inno].lastrd = time(NULL);
    inlist[inno].accp = 0777;
    inlist[inno].dirbl[0] = dbno;
    inlist[inno].md = inlist[inno].cloc = inlist[inno].slbloc = 0;

    return inno;
}

//adds a new datablock onto an inode
//sets the accounting information accordingly
//returns pointer to start of added block
char * fsys::addblock (in& ap)
{
    int rx = DBSIZE / sizeof(int);
    int dbno = superbl->getblock();
    ap.cloc = dbno;
    ap.spused = 0;
    ap.slbloc++;
    switch (ap.md)
    {
        case 0:
            if (ap.slbloc < INDB)
                ap.dirbl[ap.slbloc] = dbno;
            else
            {
                ap.md++;
                ap.sindbl = superbl->getblock();
                int2char(dblist[ap.sindbl], dbno);
                ap.slbloc = 0;
            }
            break;
        case 1:
            if (ap.slbloc < rx)
                int2char((char *)&((int *)dblist[ap.sindbl])[ap.slbloc], dbno);
            else
            {
                ap.md++;
                ap.dindbl = superbl->getblock();
                int h = superbl->getblock();
                ap.dlbloc = ap.slbloc = 0;
                int2char (dblist[ap.dindbl], h);
                int2char (dblist[h], dbno);
            }
            break;
        case 2:
            if (ap.slbloc < rx)
            {
                int h = ((int *)dblist[ap.dindbl])[ap.dlbloc];
                int2char((char *)&((int *)dblist[h])[ap.slbloc], dbno);
            }
            else
            {
                int h = superbl->getblock();
                ap.dlbloc++;
                int2char((char *)&((int *)dblist[ap.dindbl])[ap.dlbloc], h);
                int2char (dblist[h], dbno);
                ap.slbloc = 0;
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
    in * r = &inlist[pwd];
    int inno;
    if (r->spused == DBSIZE)
        u = addblock(inlist[pwd]);
    else
        u = &dblist[r->cloc][r->spused];
    snprintf(u, NAMELEN + 1, "%s", nm);
    u += NAMELEN;

    if (ty)
        inno = createdir();
    else
        inno = superbl->getinode();
    us2char(u, inno);

    inlist[inno].clear();
    inlist[pwd].fsize += TOTLEN;
    inlist[pwd].spused += TOTLEN;
    inlist[pwd].lastmod = time(NULL);

    return inno;
}

//returns char * pointing to block bno of inode up
char * fsys::getinblock (int bno, in * up)
{
    if (!up->ftype)
    {
        cout << "\nError: Search Location is not a directory.\n";
        return NULL;
    }
    int spill, rx = DBSIZE / sizeof(int);
    if (bno < INDB)
        return dblist[up->dirbl[bno]];
    else
    {
        bno -= INDB;
        if (bno < rx)
            return dblist[((int *)dblist[up->sindbl])[bno]];
        else
        {
            bno -= rx;
            spill = bno % rx;
            bno /= rx;
            return dblist[((int *)dblist[((int *)dblist[up->dindbl])[bno]])[spill]];
        }
    }
}

unsigned short fsys::locate (char * fn)
{
    in * up = &inlist[pwd];
    int ent = up->fsize / DBSIZE, enno = DBSIZE/TOTLEN;
    unsigned short inno = -1;
    char * search, name[NAMELEN+1];
    bool found = false;
    for (int bno = 0; bno < ent; ++bno)
    {
        search = getinblock(bno, up);
        if (search == NULL)
            return inno;
        for (int i = 0; i < enno; ++i)
        {
            snprintf(name, NAMELEN+1, "%s", search);
            if (strcmp(name, fn) == 0)
            {
                inno = *((unsigned short *)(search + NAMELEN));
                return inno;
            }
        }
    }
    return inno;
}


