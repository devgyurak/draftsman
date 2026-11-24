#include "shop/model.h"

namespace shop {

class Hiding {
 public:
  int Money = 0;  //> Money=-
  void g(int Customer) {  //> Customer=-
    Customer += Money;  //> Customer=var/r Money=member/r
    Order::Status s = Order::Status::Paid;  //> Order=shop::Order/t Status=shop::Order::Status/t Order=shop::Order/t Status=shop::Order::Status/t
    (void)s;
  }
  template <class Order>
  int h(Order o) {  //> Order=-
    Order copy = o;  //> Order=tparam/t
    return sizeof(copy);
  }
  template <class T>
  int k() {
    typename T::Line l;  //> Line=dependent/t
    return sizeof(l);
  }
  void lock() {
    Base::Tag tag;  //> Base=shop::Base/t Tag=shop::Base::Tag/t
    Base b(Base::Tag);  //> Base=shop::Base/t Base=shop::Base/r Tag=shop::Base::Tag/r
    (void)tag, (void)b;
  }
};

#define WRAP(x) x
#define STR(x) #x
#define MAKE Money(4)

inline int macros() {
  Money a = WRAP(Money(1));  //> Money=shop::Money/t Money=shop::Money/r
  const char* s = STR(Customer);  //> Customer=-
  Money b = MAKE;  //> Money=shop::Money/t
  return a.cents + b.cents + (s != nullptr);
}

inline int namespaces() {
  using namespace lib;
  Channel c;  //> Channel=lib::Channel/t
  namespace l = lib;
  l::Channel::Ptr p;  //> Channel=lib::Channel/t Ptr=lib::AutoPtr/t
  return p.get() == &c;
}

template <class T>
struct Box {
  T value;
};

template <>
struct Box<Money> {  //> Money=-
  Money value = Money(2);  //> Money=- Money=shop::Money/r
};

}  // namespace shop
