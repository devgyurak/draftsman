#include "shop/model.h"

int shop::Order::total() const {
  Helper h{1};              // shop::Helper: the class's namespace, not ::Helper around the definition
  Sib s{2};                 // shop::Sib: not lib::Sib, a base's namespace is not searched
  In in{3};                 // lib::Base::In, a base's member type
  Rate r = 4;               // the class's typedef (int)
  return h.s + s.s + in.n + r + Tag + sizeof(Tag) + sizeof(Channel);   // the base's field, the class's field
}

shop::Order::Order() : lib::Base(), m_(Money(1)), Channel(2) {   // Channel: the field
  Line l{1};
  struct Channel c{3};      // ::Channel: an elaborated name skips the field
  (void)l, (void)c;
}

shop::Order::~Order() { Helper h{1}; (void)h; }

bool shop::Order::operator==(const Order& o) const { Sib s{1}; return o.m_.v == m_.v + s.s - 1; }

shop::Order::operator Money() const { return Money(m_.v); }

shop::Money shop::Order::kDefault = Money(3);
const shop::Order::Status shop::Order::kFirst = Status(Open);

int shop::Order::Line::count() const { Helper h{n}; return h.s; }

int Ord::look() const {     // Ord is a typedef of shop::Order
  Money m = Money::Zero();
  return m.v + Count();
}

int shop::Order::enums() const {
  return sizeof(Paid) + (Paid == kFirst);   // the enumerator Order::Paid, not ::Paid
}

int shop::Order::late() const {
  Helper a{1};              // shop::Helper: the variable below is not declared yet
  int Helper = 2;
  return a.s + Helper;
}

template <class T> int shop::Vec<T>::push() {
  Inner i{1};               // shop::Inner: a dependent base is not searched
  Helper h{2};              // shop::Helper: nor is its field Helper
  T t{};
  (void)t;
  return i.s + h.s;
}

int shop::Fixed::f() {
  Inner i{1};               // shop::TBase::Inner: TBase<int> is searched
  return i.t + sizeof(Helper);   // TBase's field
}

template <class Money> int shop::Wrap<Money>::f() { Money m{}; return sizeof(m); }      // the parameter
template <class Helper> int shop::Wrap2<Helper>::f() { Helper h{}; return sizeof(h); }  // the parameter

int use() { shop::Vec<int> v; shop::Wrap<int> w; shop::Wrap2<long> w2; return v.push() + v.size() + w.f() + w2.f(); }
