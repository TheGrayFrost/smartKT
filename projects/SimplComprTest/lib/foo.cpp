#include "foo.h"  /* Include the header (not strictly necessary here) */

int Point::hamming_distance(){
  return x>0?(y>0?x+y: x-y):(y>0?y-x:(-1)*(x+y));
}

void Square::makeSquare(Point llp, int x){
  setPoint(llp);
  len = x;
}

void Circle::makeCircle(Point llp, int x){
  setPoint(llp);
  rad = x;
}

int area(Square s){
  return s.len*s.len;
}


/* initialization of static private member */
int Base::count = 0;
