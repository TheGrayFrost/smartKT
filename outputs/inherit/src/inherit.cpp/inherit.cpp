// #include <stdio.h>
#include "foo.h"  /* Include the header here, to obtain the function declaration */

int ParentClass::a = 100;
const int ParentClass::b = 200;


int main(void)
{
    struct foo_str x;
    x.x = 3;
    struct foo_str y;
    y = foo(x);  /* Use the function here */

    Snake snake;
    snake.crawl();

    /* Runtime polymorphism */
    ParentClass *p = new DerivedClass1();
    p->hello(); // Calls DerivedClass1's hello
    DerivedClass1 d;
    d.hello(1);
    d.hello(1.2);

    return 0;
}
