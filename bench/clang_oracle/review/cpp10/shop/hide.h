#pragma once
#include "g.h"
namespace hide {
struct Coin {};
struct Purse {
  Coin c_;
  Coin top() const;
  int coin() const;
};
struct Api {
  Thing t_;
  int Thing() const;
};
struct Derived : Api {
  ::Thing u_;
};
struct P {
  void set(Item Item);
  Item it_;
};
}
