#pragma once

#include "lib/ptr.h"

struct Helper {};
struct State {};

namespace shop {

struct Helper {};

struct Money {
  int cents = 0;
  Money(int c = 0) : cents(c) {}
};

class Customer {
 public:
  int id = 0;
};

class Base {
 public:
  explicit Base(int n) : n_(n) {}
  struct Tag {};

 protected:
  int n_;
};

class Order : public Base {
 public:
  struct Line {
    Money price;
    Money twice() const { return Money(price.cents * 2); }  //> Money=- Money=shop::Money/r
  };
  enum class Status { New, Paid };
  typedef lib::Channel::Ptr Feed;

  Order();
  Money total() const;
  void f();
  Line first() const { Line l; l.price = Money(3); return l; }  //> Line=- Line=shop::Order::Line/t Money=shop::Money/r
  bool paid() const { return status_ == Status::Paid; }  //> Status=shop::Order::Status/t
  void add(Money m = Money(5));  //> Money=- Money=shop::Money/r
  static Order* make();
  friend bool operator==(const Order& a, const Order& b) {  //> Order=- Order=-
    Customer c;  //> Customer=shop::Customer/t
    return a.status_ == b.status_ && c.id == 0;
  }

 private:
  Status status_ = Status::New;  //> Status=- Status=shop::Order::Status/t
  Money paid_ = Money(1);  //> Money=- Money=shop::Money/r
  static const int kLimit;
  enum { kSize = sizeof(Customer) };  //> Customer=shop::Customer/r
};

}  // namespace shop
