// Test nested template type substitution and the resulting templated types.
// #include <iostream>
// #include <complex>
// using namespace std;

template<typename V>
V fun(V arg_value) {
  return arg_value * arg_value;
}

// typedef complex<int> CXI;

template<class S, class T>
struct Dummy {
  S svar;
  T tvar;
  Dummy(S s, T t) : svar(s), tvar(t) { } ;
  auto foo() {
    return fun<S>(svar) + fun<T>(tvar);
  }

  bool member_method(T const& arg_value)
  {
    if( arg_value < this->tvar )
    {
      this->tvar = arg_value;
      return true;
    }
    return false;
  }
};

int main(int argc, char** argv)
{
  Dummy<int, float> local_p(3, 4.0);
//   cout << local_p.foo() << endl;

//   Dummy<CXI, CXI> local_q( CXI(3, 4), CXI(-4, 3) );

//   cout << local_q.foo() << endl;

  if( local_p.member_method(2) ) {
    // cout << local_p.tvar << endl;
  }

  return 0;
}