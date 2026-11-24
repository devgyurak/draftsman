#pragma once
struct Helper { int g; };                // ::Helper
struct Sib { int g; };                   // ::Sib
struct B { int g; };                     // ::B
struct Paid { int g; };                  // ::Paid
struct Tag { int g; };                   // ::Tag
struct Inner { int g; };                 // ::Inner
struct Channel { int g; };               // ::Channel
namespace a {
struct B { int a; };
struct C { int a; };
namespace inner { struct B { int i; }; struct D { int i; }; }
}
namespace lib {
struct Sib { int l; };
struct Channel { int l; };
struct Base { struct In { int n; }; int Tag; static int Count(); };
}
namespace shop {
struct Helper { int s; };
struct Sib { int s; };
struct Money { int v; Money(int x = 0) : v(x) {} static Money Zero(); };
struct Inner { int s; };
struct D { int s; };
struct C { int s; };
class Order : public lib::Base {
 public:
  enum Status { Paid, Open };
  Order();
  ~Order();
  int total() const;
  int look() const;
  int names() const;
  int late() const;
  int enums() const;
  bool operator==(const Order& o) const;
  operator Money() const;
  static Money kDefault;
  static const Status kFirst;
  struct Line { int n; int count() const; };
 private:
  typedef int Rate;
  Money m_;
  int Channel;
};
template <class T> struct TBase { struct Inner { int t; }; int Helper; };
template <class T> struct Vec : TBase<T> { int push(); int size() const { Inner i; return i.s; } };
struct Fixed : TBase<int> { int f(); };
template <class Money> struct Wrap { int f(); };
template <class T> struct Wrap2 { int f(); };
}
typedef shop::Order Ord;
