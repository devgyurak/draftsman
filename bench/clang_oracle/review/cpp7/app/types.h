#pragma once
#include "g.h"
#include "lib/money.h"
namespace app {
using lib::Money;
using Thing = lib::Item;
typedef struct Node0 { int v; } Node0;
struct Order {
  Order();
  static Money zero;
  Money total() const { Money m(1); return m; }
  int count() const {
    enum { Paid, Open };
    return sizeof(Paid);
  }
  int walk(const Node0* n) const { const Node0* p = n; return p ? p->v : 0; }
  int tryit() const;
  Money m_;
};
}
