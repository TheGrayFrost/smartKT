#ifndef TEM_H_   /* Include guard */
#define TEM_H_

namespace spandan{
  template <typename T>
  T myMax(T x, T y){
     return (x > y)? x: y;
  }
};

template <typename T>
class Array {
private:
    T *ptr;
    int size;
public:
    Array(T arr[], int s);
    void smfunc(){
      T x;
     for (int i = 0; i < size; i++){
        x += *(ptr + i);
     }
   }
};

template <typename T>
Array<T>::Array(T arr[], int s) {
    ptr = new T[s];
    size = s;
    for(int i = 0; i < size; i++)
        ptr[i] = arr[i];
}


#endif
