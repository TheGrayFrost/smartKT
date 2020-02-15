#include "tem.h"

int main(){
  int m = spandan::myMax<int>(3, 5);
  float ar[] = {1.1, 2.5, 3.2};
  Array<float> arm(ar, 3);
  arm.smfunc();
  return 0;
}
