//
// Created by Vishesh Agarwal on 19/03/18.
//

#ifndef FS_STRUCTURES_H
#define FS_STRUCTURES_H

#include <ctime>
#include <fstream>
#include <iostream>
#include <cstring>
#include <semaphore.h>

#define MAXINODE 1024   //maximum number of inodes allowed in filesystem
#define DBSIZE 256      //datablock size
#define INDB 8          //number of direct datablocks per inode
#define FDSIZE 50       //number of entries in File Descriptor Table
#define PTSIZE 25       //number of processes that can simulateously use MRFS

using namespace std;

// superblock structure
struct sb
{
    int size;				//file system size
    int maxin;				//maximum inodes supported
    int inused;				//inodes currently under use
    int maxdb;				//maximum datablocks
    int dbused;				//datablocks currently under use
    bool inbmap[MAXINODE];	//bitmap containing information about inode usage
    bool * dbbmap;			//bitmap containing information about datablock usage

    sb(int);				//constructor
    int getblock();			//returns an empty datablock
    int getinode();			//returns an empty inode
    void freeblock(int);    //free a datablock
    void freeinode(int);    //free an inode
    void dump(ofstream&);   //dump superblock onto file
    void restore(ifstream&);//restore superblock from file
    void print();
};

// inode structure
struct in
{
    bool ftype; 		//filetype: true -> directory
    int fsize;		    //filesize & spaceused in the last block of the file
    time_t lastmod;		//last modified time
    time_t lastrd;		//last read time
    int accp;			//access permissions: default 0777
    int dirbl[INDB];    //array of direct blocks & current last block
    int sindbl;		    //single indirect block
    int dindbl;		    //double indirect block

    in();				    //constructor
    void clear(); 		    //clears the inode
    void display();         //displays inode metadata
    void dump(ofstream&);   //dump inode list onto file
    void restore(ifstream&);//restore inode list from file
};

// fd table entry structure
struct fdentry
{
    int inno;
    int pointer;
    bool mode;

    fdentry() {inno = pointer = -1;}
    void clear() {inno = pointer = -1;}
};

// filesys structure
struct fsys
{
    sb * superbl;
    in inlist[MAXINODE];
    char (* dblist) [DBSIZE];
    fdentry fdtable[FDSIZE];
    int ptable[PTSIZE][2];

    explicit fsys (int);
    int createdir();
    int addentry (char *, bool = false);
    char * addblock (in&);
    unsigned short locate (char *, bool = false, bool = false);
    int getinblock (int, in *);
    int getpwd();
    void chpwd(int);
};

void us2char (char *, unsigned short);
void int2char (char *, int);
void progress_bar (double);

#endif //FS_STRUCTURES_H
