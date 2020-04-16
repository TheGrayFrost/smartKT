#include <iostream>
#include <cmath>
using namespace std;
class Complex { double re_, im_;
public:
Complex(double re, double im) : re_(re), im_(im) // Constructor
{ cout << "ctor: "; print(); }
Complex(const Complex& c) : re_(c.re_), im_(c.im_) // Copy Constructor
{ cout << "copy ctor: "; print(); }
~Complex() { cout << "dtor: "; print(); }
double norm() { return sqrt(re_*re_ + im_*im_); }
void print() { cout << "|" << re_ << "+j" << im_ << "| = " << norm() << endl; }
};
void Display(Complex c_param) { // Call by value
cout << "Display: "; c_param.print();
}
int main() {
Complex c(4.2, 5.3); // Constructor - Complex(double, double)
Display(c); // Copy Constructor called to copy c to c_param
return 0;
}