#include<iostream>

using namespace std;


class B { protected: int data_;
public:
B(int d = 0) : data_(d) { cout << "B::B(int): " << data_ << endl; }
~B() { cout << "B::~B(): " << data_ << endl; }
// ...
};
class D: public B { int info_;
public:
D(int d, int i) : B(d), info_(i) // ctor-1: Explicit construction of Base
{ cout << "D::D(int, int): " << data_ << ", " << info_ << endl; }
D(int i) : info_(i) // ctor-2: Default construction of Base
{ cout << "D::D(int): " << data_ << ", " << info_ << endl; }
~D() { cout << "D::~D(): " << data_ << ", " << info_ << endl; }
// ...
};

int main(){
B b(5);
D d1(1, 2); // ctor-1: Explicit construction of Base
D d2(3); // ctor-2: Default construction of Base

return 0;
}