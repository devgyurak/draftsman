#pragma once
#include <cstddef>
#include <functional>
#include <vector>
#include "g.h"
namespace shop {
struct Money { int v; };
struct Item {};
struct Cmp {
  bool operator()(const Item& a, const ::Item& b) const;
  Money operator+(const Money& o) const;
  Cmp& operator=(const Cmp&) = default;
  operator Money() const;
  explicit operator bool() const;
  Order* operator->();
  Key& operator[](const Session& s);
  friend bool operator==(const Cmp& a, const Order& b);
  void* operator new(std::size_t n);
};
struct Engine {
  typedef void (*Callback)(const Order*);
  typedef void (Engine::*Method)(Item&);
  using Factory = std::function<Session*(const Order&)>;
  void onOrder(Callback cb);
  Method method_;
  Factory factory_;
  void (*raw_)(Key key, Item Order);
  int (Money::*pm_)(const Key&) const;
  void set(void (*cb)(Session Session, int Key));
  std::function<void(Item Item)> named_;
  template <class C> const Item& pick(const C& c) const;
  template <class T> T make(Order o);
};
struct Model {
  using Ptr = Order*;
  struct Inner {};
};
using ModelAlias = Model;
struct User {
  ModelAlias::Ptr p_;
  ModelAlias::Inner i_;
};
struct Guarded {
#if 1
  Guarded(Item i, Key k);
#else
  Guarded(Session s);
#endif
#ifdef NEVER
  Guarded(Order o);
#endif
  void f(Item i);
};
template <class S> struct Tm {
  struct List {};
  using Vec = std::vector<Item>;
};
template <class S> struct Poller {
  Poller(typename Tm<S>::Vec& v, typename Tm<S>::List& l);
  typename Tm<S>::Vec held_;
  Tm<int>::Vec fixed_;
};
}
