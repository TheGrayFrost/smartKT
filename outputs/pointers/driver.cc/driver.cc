#include <math.h> 
#include <stdio.h> 
#include<iostream>

using namespace std;
  
void fun(int n, int* square, double* sq_root) 
{ 
    *square = n * n; 
    *sq_root = sqrt(n); 
} 
 
 int t;
int main() 
{ 
   
   int a = 1;
int b = 2;
int c = 3;
int* p;
int* q;

    int n = 10; 
    p = &a;
    q = &b;

    c = *p; 
    p = q; 
    *p = 13;
    
// Error
    
    t= t+1;
    cout << "t"<<t;

    int* s; 
   *s = 42; 
    cout << "*s" << *s;


    int sq; 
    double sq_root; 
    fun(n, &sq, &sq_root); 
  
    cout << "sq" << sq << "sq_root"<< sq_root; 


    
    // compilation error 1
    //char *str;    
   //str = "A";      
   //*(str+1) = 'n';  



   // runtime Error 2
   //char a1 ='A', b1 ='B'; 
    //const char *ptr = &a1; 



// runtime error 3
 //int* p1 = (int *)malloc(8); 
   // *p1 = 100;    
    //free(p1); 
    //*p1 = 110; 



// runtime error 4
//int *w;
//cout << *w;
  
    return 0; 
} 