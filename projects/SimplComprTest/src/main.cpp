#include "foo.h"  /* Include the header here, to obtain the function declaration */

int compare(Circle c, Square s){
  if(area(c) > area(s)){
    return 1;
  } else {
    return 0;
  }
}

extern int arrCircle[], arrSquare[];
int count = 0;
extern int maxele;

/* To demonstrate control flow graph */
int main(){
  int i = 0;
  Circle c;
  Square s;
  Point p(0, 0);
  if(Base::getCount() < 2)
    return 0;
  while(i < maxele){
    s.makeSquare(p, arrSquare[i]);
    c.makeCircle(p, arrCircle[i]);
    i++;
    if(compare(c, s)){
        count += c.p.hamming_distance();
    } else {
      count += 1;
    }
  }
  return count;
}
