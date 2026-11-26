#pragma once
#include <functional>
#include "lib/lib.h"
namespace sh {
struct Item {};
struct Order {};
struct Session {};
struct Ptr {};   // a rival of Model::Ptr
// 43: operator member functions
struct Cmp {
  bool operator()(const Item& a, const Item& b) const;
  Item& operator[](int i);
  bool operator==(const Cmp& o) const { return true; }
};
// 44: function and member function pointers; a parameter named like a class names none
struct Engine {
  typedef void (*Callback)(const Order* Item);
  typedef void (Engine::*Method)(Item&);
  using Factory = std::function<Session*(const Order&)>;
  void onOrder(Callback cb);
  Method method_;
  Factory factory_;
};
// 46: member function templates; a template parameter named like a class names none
struct Picker {
  template <class C> const Item& pick(const C& c) const;
  template <class Order> Order* make(Order o);
};
// 47: a member of an alias
struct Model { using Ptr = Order*; };
using ModelAlias = Model;
struct User { ModelAlias::Ptr p_; Ptr q_; };
// 48: constructors in #if branches of a class
struct A {
#ifdef _WIN32
  A(Session s);
#else
  A(Item i);
#endif
  void f(Order o);
};
// 54: a chain whose #else is an #error; a chain one branch of which forward-declares
#if defined(_WIN32)
struct Impl { void* h; };
#elif defined(__linux__) || defined(__APPLE__)
struct Impl { int fd; };
#else
#error "unsupported"
#endif
struct Api { Impl* p_; };
#ifdef _WIN32
struct Fwd;
#else
struct Fwd { int x; };
#endif
struct UsesFwd { Fwd* f_; };
}  // namespace sh
