#pragma once
#include "g.h"
namespace shop {
struct Cash {};
struct Lock { Lock(int) {} };
typedef enum { Gold, Silver } Metal;
enum class Stage { Paid, Open };

struct Order {
  enum { Paid, Open };
  int size() const { return sizeof(Paid); }
  int lock() const { Lock l(Paid); return 0; }
};
struct Base0 { enum { Paid = 3 }; };
struct Derived0 : Base0 {
  int size() const { return sizeof(Paid); }
};
struct Metals {
  int size() const { return sizeof(Gold); }
  int stage() const { return sizeof(Paid); }
  int cash() const { Cash c; return sizeof(Cash) + sizeof(c); }
};
}
