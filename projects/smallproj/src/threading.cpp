#include "mythread.h"
#include <thread>


int main(){
  std::thread t1(task1, 100);
  std::thread t2(task1, 100);
  std::thread t3(task1, 100);

  t1.join();
  t2.join();
  t3.join();
  return 0;
}
