
#include "foo.hh"

// #include <iostream>

namespace Foo {

  void fun(int arg_x, int arg_y) {
    // std::cout << (arg_x*arg_y-arg_x-arg_y+1) << std::endl;
      // week day;
      // A r;
      // B q;
      // day = M;
  }

  void fun(int arg_x) {
    // std::cout << (arg_x*arg_y-arg_x-arg_y+1) << std::endl;
      int u;
      A r;
      B q;
      u = arg_x;
  }

  template<typename T1, typename T2>
  bool tfun(T1 targ_x, T2 targ_y) {
    int local_x = targ_x + targ_y;
    if( local_x == -8 ) return false;
    return targ_x < targ_y;
  }

  // template<int, typename T2>
  // bool tfun(int targx, T2 targy) {
  //   return targx == targy;
  // }

  template<> bool tfun<float, float>(float x, float y) {
  	return x > y;
  }

  week day;
  A r;
  B q;

  lli m;
}
