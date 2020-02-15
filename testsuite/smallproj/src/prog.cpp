// #include <stdio.h>
#include "foo.h"  /* Include the header here, to obtain the function declaration */

int main(void)
{
    struct foo_str x;
    x.x = 3;
    struct foo_str y;
    y = foo(x);  /* Use the function here */

    Snake snake;
    snake.crawl();
    return 0;
}
