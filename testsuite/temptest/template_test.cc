// Test nested template type substitution and the resulting templated types.
// #include <iostream>
// #include <complex>
// using namespace std;
#include <cstdio>

template<typename V>
V fun(V arg_value) {
  return arg_value * arg_value;
}

// typedef complex<int> CXI;
int not_a_template = 42;

bool omg() {return true;}

template<class S, class T>
struct Dummy {
  S svar;
  T tvar;
  int ivar;
  static T jvar;

  Dummy(S s, T t) : svar(s), tvar(t) { } ;
  T foo() {
    return fun<S>(svar) + fun<T>(tvar) + jvar;
  }

  bool member_method(T const& arg_value)
  {
    if( arg_value < this->tvar )
    {
      this->tvar = this->foo();

      return omg();
    }
    return false;
  }

  virtual void reality() { };
};

struct nontempDummy
{
  auto foo() {
    return fun<int>(4) + fun<float>(3.5) + 6;
  }

  bool member_method() {
    auto r = foo();
    return omg();}
};

// explicit definition for static variable in class
template <class S, class T>
T Dummy<S, T>::jvar;

int main(int argc, char** argv)
{
  Dummy<int, float> local_p(3, 4.0);

//   cout << local_p.foo() << endl;

//   Dummy<CXI, CXI> local_q( CXI(3, 4), CXI(-4, 3) );

//   cout << local_q.foo() << endl;

  if( local_p.member_method(2) ) {
    local_p.svar = 5;
    local_p.ivar = 3;
  }

  Dummy<float, int> isThis(3.0, 4);
  isThis.reality();
  not_a_template = 43;

  return 0;
}
