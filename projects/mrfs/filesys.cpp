//
// Created by Vishesh Agarwal on 19/03/18.
//

#include "filesys.h"

fsys * myfs;

int create_myfs (int size)
{
    try
    {
        cout << "\nCreating file system of size: " << size << "MB.\n\n";
        myfs = new fsys(size);
        cout << "Filesystem created successfully.\n\n";
        return 0;
    }

    catch (int e)
    {
        cout << e << ": An exception occured in filesys creation.\n";
        return -1;
    }
}

//copies file src from pc
//to location dest in myfs
//returns 0 if operation successful
//returns -1 if unsuccessful
int copy_pc2myfs(char * src, char * dest)
{
    cout << "Trying to copy file: " << src << " from PC to MRFS at: " << dest << "\n\n";

    ifstream fp (src, ios::in|ios::binary);

    if (!fp.is_open())
    {
        cout << src << ": File does not exist.\nCopy operation aborted.\n\n";
        return -1;
    }

    cout << "File opened: " << src << "\n";

    long r = fp.tellg();
    fp.seekg(0, ios::end);
    long fs = fp.tellg() - r;
    fp.seekg(0);

    cout << "Bytes to be copied: " << fs << "\n";

    int rx = DBSIZE / sizeof(int);
    int maxfs = (INDB + rx + rx * rx) * DBSIZE;
    if (fs > maxfs)
    {
        cout << "Error: File is too large for MRFS. Max supported size is: ";
        cout << maxfs << " bytes.\n Copy operation aborted.\n\n";
        return -1;
    }


    int curinno = myfs->addentry(dest);
    char * here;

    cout << "\nCopy operation initiated.\n\nProgress:\n";

    while (myfs->inlist[curinno].fsize < fs)
    {
        here = myfs->addblock(myfs->inlist[curinno]);
        if (!fp.read (here, DBSIZE))
            fp.clear();
        myfs->inlist[curinno].fsize += fp.gcount();
        myfs->inlist[curinno].lastmod = time(NULL);
        progress_bar(myfs->inlist[curinno].fsize * 1.0 / fs);
    }
    cout << "\nCopied: " << myfs->inlist[curinno].fsize << "/" << fs <<" bytes to " << dest << ".\n";

    if (myfs->inlist[curinno].fsize == fs)
        cout << "\nFile copied successfully.\n\n";
    else
    {
        cout << "\nCopy operation unsuccessful.\n\n";
        return -1;
    }

    fp.close();
    return 0;
}

//copies file src from myfs
//to location dest on pc
//returns 0 if operation successful
//returns -1 if unsuccessful
int copy_myfs2pc(char * src, char * dest)
{
    cout << "Trying to copy file: " << src << " from MRFS to PC at: " << dest << "\n\n";

    int curfs, fs, i, copied;
    char * here;

    unsigned short r = myfs->locate(src);
    if (r == (unsigned short)-1)
    {
        cout << "Error: Source file could not be located.\nCopy operation aborted.\n\n";
        return -1;
    }

    cout << "Source file located and opened for copying.\n";

    ofstream fp (dest, ios::out|ios::binary);
    cout << "Destination File opened for writing: " << dest << "\n";

    curfs = fs = myfs->inlist[r].fsize;
    cout << "Bytes to be copied: " << fs << "\n";

    cout << "\nCopy operation initiated.\n\nProgress:\n";

    i = 0;
    copied = 0;
    while (curfs > 0)
    {
        here = myfs->dblist[myfs->getinblock(i, &myfs->inlist[r])];
        if (curfs >= DBSIZE)
        {
            fp.write (here, DBSIZE);
            copied += DBSIZE;
        }
        else
        {
            fp.write (here, curfs);
            copied += curfs;
        }
        progress_bar(copied * 1.0 / fs);
        curfs -= DBSIZE;
        i++;
    }

    cout << "\nCopied: " << copied << "/" << fs <<" bytes to " << dest << ".\n";
    if (copied == fs)
        cout << "\nFile copied successfully.\n\n";
    else
    {
        cout << "\nFile copy operation unsuccessful.\n\n";
        return -1;
    }

    fp.close();
    return 0;
}

int rm_myfs (char * fname)
{
    cout << "Trying to delete file: " << fname << "\n";
    unsigned short r = myfs->locate(fname, true);
    if (r == (unsigned short)-1)
    {
        cout << "\nError: File could not be located.\nDelete operation aborted.\n\n";
        return -1;
    }
    else if (r == (unsigned short)-2)
    {
        cout << "\nError: " << fname << " is a directory.\nDelete operation aborted.\n\n";
        return -1;
    }
    cout << "\nFile located.\nDelete operation initiated.\n\nProgress:\n";
    in * rm = &myfs->inlist[r];
    int ent = rm->fsize / DBSIZE;
    ent += (rm->fsize % DBSIZE ? 1 : 0);
    for (int i = 0; i < ent; ++i)
    {
        myfs->superbl->freeblock(myfs->getinblock(i, rm));
        progress_bar((i+1) * 1.0 / ent);
    }
    myfs->superbl->freeinode(r);
    cout << "\nDeleted file: " << fname << "\n\nDelete operation successful.\n\n";
    return 0;
}

//displays contents of a file in the pwd
int showfile_myfs (char * fname)
{
    unsigned short r = myfs->locate(fname);
    if (r == (unsigned short)-1)
    {
        cout << "\nError: File could not be located.\nDisplay operation aborted.\n\n";
        return -1;
    }
    cout << "\nFile located.\nDisplay operation initiated.\n";
    in * show = &myfs->inlist[r];
    if (show->ftype)
    {
        cout << "Error: " << fname << " is a directory.\nDisplay operation aborted.\n\n";
        return -1;
    }

    cout << "Displaying file: " << fname << "\n\n";
    int ent = show->fsize / DBSIZE, spill = show->fsize % DBSIZE, l = DBSIZE;
    ent -= (spill ? 0 : 1);
    spill = (spill ? spill : DBSIZE);
    for (int i = 0; i <= ent; ++i)
    {
        if (i == ent)
            l = spill;
        cout.write(myfs->dblist[myfs->getinblock(i, show)], l);
        cout.flush();
    }
    cout << "\n\n";
    return 0;
}


//displays files in the pwd
int ls_myfs ()
{
    in * up = &myfs->inlist[myfs->getpwd()];
    int ent = up->fsize / DBSIZE, lno = up->fsize % DBSIZE, enno = DBSIZE/TOTLEN, loc;
    ent -= (lno ? 0 : 1);
    lno = (lno ? lno : DBSIZE);
    lno /= TOTLEN;
    unsigned short inno = -1;
    char * search, name[NAMELEN+1];

    for (int bno = 0; bno <= ent; ++bno)
    {
        loc = myfs->getinblock(bno, up);
        if (loc == -1)
            return inno;
        search = myfs->dblist[loc];
        if (bno == ent)
            enno = lno;
        for (int i = 0; i < enno; ++i)
        {
            snprintf(name, NAMELEN+1, "%s", search);
            if ((strcmp(name, ".") != 0) && (strcmp(name, "..") != 0))
            {
                inno = *((unsigned short *) (search + NAMELEN));
                myfs->inlist[inno].display();
                cout << name << "\n";
            }
            search += TOTLEN;
        }
    }
    cout << "\n\n";
    return 0;
}

//creates new directory in pwd
//if it doesn't already exist
int mkdir_myfs (char * dname)
{
    cout << "Attempting to create directory: " << dname << "\n";
    unsigned short r = myfs->locate(dname);
    if (r != (unsigned short) -1)    //can't create directory if already present
    {
        cout << "Error: " << dname << ": File already exists.\nCreate directory operation aborted.\n\n";
        return -1;
    }
    myfs->addentry(dname, true);
    cout << "Directory created successfully.\n\n";
    return 0;
}

//changes to directory in pwd
int chdir_myfs (char * dname)
{
    cout << "Attempting to change to directory: " << dname << "\n";
    unsigned short r = myfs->locate(dname);
    if (r == (unsigned short) -1)    //can't change directory if not already present
    {
        cout << "Error: " << dname << ": Directory not found.\nChange directory operation aborted.\n\n";
        return -1;
    }
    myfs->chpwd(r);
    cout << "Working directory changed successfully.\n\n";
    return 0;
}

//removes directory in pwd
int rmdir_myfs (char * dname)
{
    cout << "Attempting to remove directory: " << dname << "\n";
    unsigned short r = myfs->locate(dname, true, true);
    if (r == (unsigned short) -1)    //can't remove directory if not already present
    {
        cout << "Error: " << dname << ": Directory not found.\nRemove directory operation aborted.\n\n";
        return -1;
    }
    if (myfs->inlist[r].fsize > 2 * TOTLEN)
    {
        cout << "Error: Directory is not empty.\nRemove directory operation aborted.\n\n";
        return -1;
    }

    in * rm = &myfs->inlist[r];
    int ent = rm->fsize / DBSIZE;
    ent += (rm->fsize % DBSIZE ? 1 : 0);
    for (int i = 0; i < ent; ++i)
        myfs->superbl->freeblock(myfs->getinblock(i, rm));
    myfs->superbl->freeinode(r);

    cout << "Directory removed successfully.\n\n";
    return 0;
}


//opens a file
//returns the file descriptor
//takes care of read-write clashes
int open_myfs (char * fname, char mode)
{
    bool md;
    in * opened;
    cout << "Attempting to open file " << fname << " in '" << mode << "' mode.\n";

    switch(mode)
    {
        case 'r': md = false; break;
        case 'w': md = true; break;
        default: cout << "Invalid mode.\nOpen opertaion aborted.\n\n"; return -1;
    }

    unsigned short r = myfs->locate(fname);

    if (r == (unsigned short)-1)    //create file if not already present
    {
        r = myfs->addentry(fname);
        opened = &myfs->inlist[r];
    }
    else
    {
        opened = &myfs->inlist[r];

        if (opened->ftype)
        {
            cout << "Error: " << fname << " is a directory.\nOpen opertaion aborted.\n\n";
            return -1;
        }

        //check for existing entries
        for (int i = 0; i < FDSIZE; ++i)
        {
            if (myfs->fdtable[i].inno == r)
            {
                if (myfs->fdtable[i].mode)
                {
                    cout << "Error: File is already open in write mode.\nOpen opertaion aborted.\n\n";
                    return -1;
                }
                else if (md)
                {
                    cout << "Error: File is already open in read mode.\nPlease wait for the read sessions to finish before opening file in write mode.\nOpen opertaion aborted.\n\n";
                    return -1;
                }
            }
        }

        if (md)     // if file is to be opened in write mode, clear file contents
        {
            int ent = opened->fsize / DBSIZE;
            ent += (opened->fsize % DBSIZE ? 1 : 0);
            for (int j = 0; j < ent; ++j)
                myfs->superbl->freeblock(myfs->getinblock(j, opened));
            opened->fsize = 0;
        }
    }

    int ffi = 0;
    while ((ffi < FDSIZE) && (myfs->fdtable[ffi].inno != -1))
        ffi++;

    if (ffi == FDSIZE)
    {
        cout << "Error: Maximum file open limit reached.\nOpen opertaion aborted.\n\n";
        return -1;
    }

    myfs->fdtable[ffi].inno = r;
    myfs->fdtable[ffi].pointer = 0;
    myfs->fdtable[ffi].mode = md;

    cout << "File opened successfully.\n\n";

    return ffi;
}

//closes a file
int close_myfs (int fd)
{
    if ((fd >= FDSIZE) || (myfs->fdtable[fd].inno == -1))
    {
        cout << "Bad file descriptor.\nClose operation aborted.\n\n";
        return -1;
    }

    if (myfs->fdtable[fd].mode)
        myfs->inlist[myfs->fdtable[fd].inno].lastmod = time(NULL);
    else
        myfs->inlist[myfs->fdtable[fd].inno].lastrd = time(NULL);
    myfs->fdtable[fd].inno = -1;
    cout << "File closed successfully.\n\n";

    return 0;
}

//reads nbytes from file descriptor
//reads characters into buff
int read_myfs(int fd, int nbytes, char * buff)
{
    int init = myfs->fdtable[fd].pointer;
    if ((fd >= FDSIZE) || (myfs->fdtable[fd].inno == -1))
    {
        cout << "Bad file descriptor.\nRead operation aborted.\n\n";
        return -1;
    }

    if (myfs->fdtable[fd].mode)
    {
        cout << "File is open in write mode. Cannot perform read.\nRead operation aborted.\n\n";
        return -1;
    }

    try
    {
        in * copy = &myfs->inlist[myfs->fdtable[fd].inno];
        int inibno = myfs->fdtable[fd].pointer / DBSIZE, spill = myfs->fdtable[fd].pointer % DBSIZE;
        char *  here = myfs->dblist[myfs->getinblock(inibno, copy)];
        here += spill;
        int copied = DBSIZE - spill;
        if (copied > nbytes)
            copied = nbytes;
        if (myfs->fdtable[fd].pointer + copied > copy->fsize)
            copied = copy->fsize - myfs->fdtable[fd].pointer;

        while ((nbytes > 0) && (myfs->fdtable[fd].pointer < copy->fsize))
        {
            memcpy(buff, here, copied);
            nbytes -= copied;
            buff += copied;
            inibno++;
            myfs->fdtable[fd].pointer += copied;
            copied = DBSIZE;
            copied = (nbytes > DBSIZE ? DBSIZE : nbytes);
            if (myfs->fdtable[fd].pointer + copied > copy->fsize)
                copied = copy->fsize - myfs->fdtable[fd].pointer;
            if ((myfs->fdtable[fd].pointer < copy->fsize) && (nbytes > 0))
                here = myfs->dblist[myfs->getinblock(inibno, copy)];
        }

        if (myfs->fdtable[fd].pointer > copy->fsize)
        {
            cout << "Error: Attempt to read past end of file.\nRead operation failed.\n\n";
            return -1;
        }
    }

    catch (int e)
    {
        cout << "Errno: " << e << " occured.\nRead operation aborted.\n\n";
        return -1;
    }

    return (myfs->fdtable[fd].pointer - init);
}


//writes nbyte characters from buff to fd
int write_myfs(int fd, int nbytes, char * buff)
{
    int init = myfs->fdtable[fd].pointer;
    if ((fd >= FDSIZE) || (myfs->fdtable[fd].inno == -1))
    {
        cout << "Bad file descriptor.\nWrite operation aborted.\n\n";
        return -1;
    }

    if (!myfs->fdtable[fd].mode)
    {
        cout << "File is open in read mode. Cannot perform write.\nWrite operation aborted.\n\n";
        return -1;
    }

    try
    {
        int r = myfs->fdtable[fd].inno;
        in * copy = &myfs->inlist[r];
        char *  here;
        int inibno = myfs->fdtable[fd].pointer / DBSIZE, spill = myfs->fdtable[fd].pointer % DBSIZE;

        if (spill == 0)
            here = myfs->addblock(myfs->inlist[r]);
        else
            here = myfs->dblist[myfs->getinblock(inibno, copy)];
        here += spill;

        int copied = DBSIZE - spill;
        if (copied > nbytes)
            copied = nbytes;

        while (nbytes > 0)
        {
            memcpy(here, buff, copied);
            nbytes -= copied;
            buff += copied;
            copy->fsize += copied;
            myfs->fdtable[fd].pointer += copied;
            copied = DBSIZE;
            copied = (nbytes > DBSIZE ? DBSIZE : nbytes);
            if (nbytes > 0)
                here = myfs->addblock(myfs->inlist[r]);
        }
    }

    catch (int e)
    {
        cout << "Errno: " << e << " occured.\nWrite operation aborted.\n\n";
        return -1;
    }

    return (myfs->fdtable[fd].pointer - init);
}



//checks if end of file has been reached
int eof_myfs (int fd)
{
    if ((fd >= FDSIZE) || (myfs->fdtable[fd].inno == -1))
    {
        cout << "Bad file descriptor.\nClose operation aborted.\n\n";
        return -1;
    }

    if (myfs->fdtable[fd].pointer == myfs->inlist[myfs->fdtable[fd].inno].fsize)
        return 1;

    return 0;
}

//dumps MRFS to a secondary file on PC
int dump_myfs (char * dumpfile)
{
    cout << "Attempting to dump MRFS to " << dumpfile << "\n";
    ofstream fp (dumpfile, ios::out|ios::binary);
    if (fp.fail())
    {
        cout << "Error: " << dumpfile << " could not be opened properly.\nDump operation aborted.\n\n";
        return -1;
    }

    myfs->superbl->dump(fp);
    cout << "Superblock dumped.\n";
    for (int i = 0; i < MAXINODE; ++i)
        myfs->inlist[i].dump(fp);
    cout << "Inode list dumped.\n";
    for (int i = 0; i < myfs->superbl->maxdb; ++i)
        fp.write(myfs->dblist[i], DBSIZE);
    cout << "Data blocks dumped.\n";
    fp.close();

    cout << "MRFS dumped successfully.\n\n";
    return 0;
}

//restores MRFS from a secondary file on PC
int restore_myfs (char * dumpfile)
{
    cout << "Attempting to restore MRFS from " << dumpfile << "\n";
    ifstream fp (dumpfile, ios::in|ios::binary);
    if (fp.fail())
    {
        cout << "Error: " << dumpfile << " could not be opened properly.\nRestore operation aborted.\n\n";
        return -1;
    }

    myfs->superbl->restore(fp);
    cout << "Superblock restored.\n";
    for (int i = 0; i < MAXINODE; ++i)
        myfs->inlist[i].restore(fp);
    cout << "Inode list restored.\n";
    for (int i = 0; i < myfs->superbl->maxdb; ++i)
        fp.read(myfs->dblist[i], DBSIZE);
    cout << "Data blocks restored.\n";
    fp.close();

    for (int i = 0; i < FDSIZE; ++i)
        myfs->fdtable[i].clear();
    cout << "File descriptor table reset.\n";
    for (int i = 0; i < PTSIZE; ++i)
        myfs->ptable[i][0] = myfs->ptable[i][1] = -1;
    cout << "Process table reset.\n";

    cout << "MRFS restored successfully.\n\n";
    return 0;
}

//prints basic filesystem information
int status_myfs()
{
    cout << "File system status:\n\n";
    myfs->superbl->print();
    return 0;
}

//changes mode of file in pwd
int chmod_myfs(char * fname, int newmd)
{
    cout << "Attempting to change access permissions for file: " << fname << "\n";
    unsigned short r = myfs->locate(fname);
    if (r == (unsigned short)-1)
    {
        cout << "Error: File could not be located.\nMode change operation aborted.\n\n";
        return -1;
    }

    myfs->inlist[r].accp = newmd;
    myfs->inlist[r].lastmod = time(NULL);
    cout << "Mode changed successfully.\n\n";
    return 0;
}

