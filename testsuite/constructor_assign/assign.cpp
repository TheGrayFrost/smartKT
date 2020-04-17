#include <iostream>
#include <cstdlib>
#include <cstring>
using namespace std;
class String { public: char *str_; size_t len_;
String(char *s) : str_(strdup(s)), len_(strlen(str_)) { } // ctor
String(const String& s) : str_(strdup(s.str_)), len_(s.len_) { } // cctor
~String() { free(str_); } // dtor
String& operator=(const String& s) {
free(str_); // Release existing memory
str_ = strdup(s.str_); // Perform deep copy
len_ = s.len_;
return *this; // Return object for chain assignment
}
void print() { cout << "(" << str_ << ": " << len_ << ")" << endl; }
};
int main() { String s1 = "Football", s2 = "Cricket";
s1.print(); s2.print();
s2 = s1; s2.print();
return 0;
}