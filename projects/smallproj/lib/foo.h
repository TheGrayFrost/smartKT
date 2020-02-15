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

/* CLASSES */
class ParentClass{
  int x, y, z;
  static int a;
public:
  const static int b;
  int c;
  float d;
  enum days{sun, mon, tue, wed, thrus, fri, sat};
  union month{
    int x;
    float f;
  };
  virtual void hello(){
    this->x = y + ParentClass::a;
  }
  friend class ParentClass1;
  friend void accessFriendClassGlobal();
};

/* INHERITANCE & FUNCTION OVERLOADING */
class DerivedClass1: public ParentClass{
public:
  void hello(){
    this->c = ParentClass::b;
  }

  void hello(int i){
    this->c = i;
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
struct MI: public foo_str, private ParentClass{
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

class Snake : protected Animal, public Reptile {
public:
  void crawl();
};

#endif // FOO_H_
