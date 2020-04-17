#ifndef FOO_H_   /* Include guard */
#define FOO_H_


/* STRUCTS */
struct foo_str{
  int x;
  int y;
private:
  int z;
};

struct foo_str foo(struct foo_str x);  /* An example function declaration */

namespace nonstd {

/* CLASSES */
class ParentClass{
  int x, y, z;
  static int alpha, beta;
public:
  const static int gamma;
  int c;
  float d;
  enum days{sun, mon, tue, wed, thrus, fri, sat};
  union month{
    int x;
    float f;
  };
  virtual void hello(){
    this->x = y + ParentClass::alpha;
  }
  friend class ParentClass1;
  friend void accessFriendClassGlobal();
};

/* INHERITANCE & FUNCTION OVERLOADING */
class DerivedClass1: public ParentClass{
public:
  void hello(){
    this->c += ParentClass::gamma;
    (this->c)++;
  }

  void hello(int i){
    this->c = i = 9;
  }

  void hello(double z){
    this->d += z;
  }
};

/* FRIEND FUNCTIONS */
class ParentClass1 {
  ParentClass p;
public:
  void accessFriendClass(){
    p.x = 5;
  }
};

/* MULTIPLE INHERITANCE */
struct MI: ParentClass, public foo_str{
public:
  int do_nothing(){
    return 5;
  }
};

/* VIRTUAL INHERITANCE */
class LivingThing {
protected:
    bool isBreathing;
    void breathe() {
        this->isBreathing = true;
    }
public:
  LivingThing(){
    this->isBreathing = false;
  }
};

class Animal : virtual protected LivingThing {
protected:
    int breathCount;
    void breathe() {
        this->breathCount++;
    }
public:
  Animal(){
    this->breathCount = 0;
  }
};

class Reptile : virtual public LivingThing {
public:
  bool isCrawling;

  Reptile(){
    this->isCrawling = true;
  }
protected:
    void crawl() {
      this->isCrawling = true;
    }
};

class Snake : protected Animal, Reptile, ParentClass {
public:
  void crawl();
};

};

#endif // FOO_H_
