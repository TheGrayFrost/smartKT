#include "bar.h"

int main(){
  extern int x;
  int c = NS1::y + NS1::NS2::d + x;
  return c;
}
