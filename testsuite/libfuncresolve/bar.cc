#include <iostream>

void foo1();

void bar()
{
	std::cout << "In bar.cc's bar()\n";
	foo1();
}