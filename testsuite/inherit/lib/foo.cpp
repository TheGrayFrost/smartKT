#include "foo.h"  /* Include the header (not strictly necessary here) */

struct foo_str foo(struct foo_str x)    /* Function definition */
{
    x.x += 5;
    return x;
}

void accessFriendClassGlobal(){
  nonstd::ParentClass p;
  // p.x = 7;
}

void nonstd::Snake::crawl() {
    this->breathe();
    this->isCrawling = true;
}
