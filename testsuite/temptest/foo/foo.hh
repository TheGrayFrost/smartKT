// Dummy test library.

#ifndef __FOO_HH__
#define __FOO_HH__

#define lli long long int

namespace Foo {

  // void fun(int, int);

  template<typename T1, typename T2> bool tfun(T1, T2);

  struct A {
  		char y;
  		int x;
  	};

  class B {
  private:
  	char y;
  	char z[4];
  public: 
    char a;
  	B() {;}
  };

  enum week{M, T, F};
}

#endif
