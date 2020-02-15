#ifndef MYTHREAD_H_   /* Include guard */
#define MYTHREAD_H_

class A{
public:
  int x;
  A(){
    this->x = 0;
  }
};

A a;

void task1(int x){
  for(int i=0; i<x; i++)
    a.x+=1;
}

#endif
