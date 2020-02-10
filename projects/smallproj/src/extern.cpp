#include "bar.h"

int main(){
  extern int x;
  int c = NS1::y + NS1::a + NS1::NS2::c + NS1::NS2::d;
  return c;
}
