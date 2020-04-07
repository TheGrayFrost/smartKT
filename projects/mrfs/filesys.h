//
// Created by Vishesh Agarwal on 19/03/18.
//

#ifndef FS_FILESYS_H
#define FS_FILESYS_H

#include "structures.h"

#define NAMELEN 30
#define INLEN 2
#define TOTLEN (NAMELEN + INLEN)

int create_myfs (int);
int copy_pc2myfs(char *, char *);
int copy_myfs2pc(char *, char *);
int rm_myfs(char *);
int showfile_myfs(char *);
int ls_myfs();
int mkdir_myfs(char *);
int chdir_myfs(char *);
int rmdir_myfs(char *);
int open_myfs(char *, char);
int close_myfs(int);
int read_myfs(int, int, char *);
int write_myfs(int, int, char *);
int eof_myfs(int);
int dump_myfs(char *);
int restore_myfs(char *);
int status_myfs();
int chmod_myfs(char *, int);

#endif //FS_FILESYS_H
