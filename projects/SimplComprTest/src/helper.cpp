#include "foo.h"

int area(Circle c){
  return 3 * c.rad * c.rad;
}

int compare(Circle c, Square s);

/* Extern linkage of variables and arrays */

extern int count;
int maxele = 5;
int arrCircle[5] = {1, 2, 3, 4, 5};
int arrSquare[5] = {6, 5, 4, 3, 2};
