#pragma once
#include "lib/lib.h"
namespace la = lib;
namespace shop2 {
using lib::Item;
struct A {
  la::Money m_;
  Item i_;
  la::Box<Item> b_;
  la::Base::Inner n_;
};
namespace in {
struct Item {};
struct B {
  Item i_;
  ::Item g_;
};
}
struct C : la::Base {
  C() : la::Base(1) {}
};
struct Dd : Item {};
}
