#include <memory>
#include <vector>

#include "shop/model.h"

namespace shop {

// out of the class: its members, its bases, the namespaces around the class
Order::Order() : Base(1), status_(Status::New) {  //> Order=- Order=- Base=shop::Base/r Status=shop::Order::Status/t
  Tag t;  //> Tag=shop::Base::Tag/t
  (void)t;
}

Money Order::total() const {  //> Money=- Order=-
  std::vector<Money> all{Money(1), Money(2)};  //> Money=shop::Money/t Money=shop::Money/r Money=shop::Money/r
  Money sum;  //> Money=shop::Money/t
  for (const Money& m : all) sum.cents += m.cents;  //> Money=shop::Money/t
  return sum;
}

void Order::add(Money m) {  //> Order=- Money=-
  Line* l = new Line;  //> Line=shop::Order::Line/t Line=shop::Order::Line/t
  l->price = m;
  delete l;
  Feed feed;  //> Feed=lib::AutoPtr/t
  (void)feed;
}

Order* Order::make() {  //> Order=- Order=-
  auto made = std::make_unique<Order>();  //> Order=shop::Order/t
  return static_cast<Order*>(made.release());  //> Order=shop::Order/t
}

const int Order::kLimit = sizeof(Money);  //> Order=- Money=shop::Money/t

}  // namespace shop

// written outside namespace shop: the names are looked up in Order, Base, shop, then ::
void shop::Order::f() {  //> Order=-
  Helper h;  //> Helper=shop::Helper/t
  ::Helper g;  //> Helper=Helper/t
  shop::Customer c;  //> Customer=shop::Customer/t
  Order::Line line;  //> Order=shop::Order/t Line=shop::Order::Line/t
  (void)h, (void)g, (void)c, (void)line;
  auto check = [](const Money& m) { Customer who; return m.cents + who.id; };  //> Money=shop::Money/t Customer=shop::Customer/t
  struct Local {
    Money m() { return Money(9); }  //> Money=shop::Money/t Money=shop::Money/r
  };
  (void)check;
}
