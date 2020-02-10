#ifndef BAR_H_   /* Include guard */
#define BAR_H_

extern int x;

namespace NS1{
  extern int y;
  int a, b;
  namespace NS2{
    int c;
    extern int d;
  }
};

#endif
