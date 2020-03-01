// Test nested template type substitution and the resulting templated types.
#include <iostream>
#include <complex>
using namespace std;

template<typename V>
V fun(V arg_value) {
  return arg_value * arg_value;
}

typedef complex<int> CXI;

template<class S, class T>
struct Dummy {
  S svar;
  T tvar;
  Dummy(S s, T t) : svar(s), tvar(t) { } ;
  auto foo() {
    return fun<S>(svar) + fun<T>(tvar);
  }
};

int main(int argc, char** argv)
{
  Dummy<int, float> p(3, 4.0);
  cout << p.foo() << endl;

  Dummy<CXI, CXI> q( CXI(3, 4), CXI(-4, 3) );

  cout << q.foo() << endl;

  return 0;
}