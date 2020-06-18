#ifndef FOO_H_   /* Include guard */
#define FOO_H_

// Classes  and Inheritance
struct Point {
  int x, y;
  Point(int a, int b): x(a), y(b){}
  Point(){}
  int hamming_distance();
};


class Base {
  static int count;
public:
  Point p;

  // Explicit destructors
  Base(){
    count += 1;
  }

  // Explicit destructors
  ~Base(){
    count -= 1;
  }

  void setPoint(Point x){ p = x;}

  /* With a static member */
  static int getCount(){ return count; }
};

class Square: public Base {
public:
  int len;

  void makeSquare(Point llp, int x);
};

class Circle: public Base {
public:
  int rad;

  void makeCircle(Point llp, int x);
};

/* Function overloading */
int area(Square s);
int area(Circle c);

#endif // FOO_H_
