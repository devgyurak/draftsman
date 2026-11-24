#include <sys/time.h>

#include <map>
#include <typeinfo>

#include "shop/model.h"

// a type and a namespace of one name: the namespace is nearer
struct Keywords {
  static int now() { return 2; }
};

namespace shop {

namespace Keywords {
inline int now() { return 1; }
}  // namespace Keywords

struct Panel {
  int f() { return Keywords::now(); }  //> Keywords=namespace/t
};

// `Guard g(Tag);` with a variable Tag: a variable g, not a function declaration
struct Tag {};
struct Guard {
  explicit Guard(int) {}
};
struct User {
  int Tag = 0;
  void f() {
    Guard g(Tag);  //> Guard=shop::Guard/t Tag=member/r
    (void)g;
  }
};

// a function of the class's name hides the class: `Ticket(1)` calls it
struct Ticket {
  int n;
};
inline int Ticket(int n) { return n; }
struct Desk {
  int f() { return Ticket(1); }  //> Ticket=function/r
};

// an alias template's own parameters are no types
struct Hash {};
template <class K, class Hash = int>
using Table = std::map<K, Hash>;
struct Store {
  int n() const {
    Table<int> t;  //> Table=shop::Table/t
    return static_cast<int>(t.size());
  }
};

// a class's own alias comes first in a qualified name: Poller's Mutex is FastMutex
template <class M>
struct Lock {
  explicit Lock(M&) {}
};
struct FastMutex {
  using ScopedLock = Lock<FastMutex>;
};
struct Mutex {
  using ScopedLock = Lock<Mutex>;
};
struct Poller {
  using Mutex = FastMutex;
  using ScopedLock = Mutex::ScopedLock;
  FastMutex m_;
  void f() {
    ScopedLock l(m_);  //> ScopedLock=shop::Lock/t
    (void)l;
  }
};

// an alias of a dependent name answers nothing until the template is instantiated
template <class C>
struct Holder {
  using Ptr = Lock<C>;
};
template <class C>
struct Watcher {
  using Ptr = typename Holder<C>::Ptr;
  void f(C* c) {
    Ptr p(*c);  //> Ptr=shop::Watcher::Ptr/t
    (void)p;
  }
};

// an operator, a destructor and a conversion defined in the class; `typeid`, an alias's
// constructor
struct Pricing {
  using Cash = Money;
  bool operator<(const Pricing&) const {  //> Pricing=-
    Money m;  //> Money=shop::Money/t
    return m.cents < 0;
  }
  ~Pricing() {  //> Pricing=-
    Customer c;  //> Customer=shop::Customer/t
    (void)c;
  }
  explicit operator bool() const { return typeid(Money) == typeid(Customer); }  //> Money=shop::Money/r Customer=shop::Customer/r
  template <class T>
  Pricing& operator<<(const T&) {  //> Pricing=-
    Money m = Cash(2);  //> Money=shop::Money/t Cash=shop::Money/r
    (void)m;
    return *this;
  }
};

}  // namespace shop

// a type declared in an `#if` branch no build takes: the system's timeval is meant
#ifdef SHOP_OLD_LIBC
struct timeval {
  long tv_sec;
};
#endif

namespace shop {

struct Clock {
  long now() const {
    timeval tv{};  //> timeval=timeval/t
    return static_cast<long>(tv.tv_sec);
  }
  void name(int n);
  Money price(Customer c) const;
};

// an `#if` inside a function whose branches each open a block: the parser takes the
// functions after it for the function's body
void Clock::name(int n) {
  int half = 0;
#if defined(SHOP_MAC)
  if (n > 31) {
    half = 15;
#else
  if (n > 15) {
    half = 7;
#endif
  }
  (void)half;
}

Money Clock::price(Customer c) const {  //> Money=- Clock=- Customer=-
  return Money(c.id);  //> Money=shop::Money/r
}

}  // namespace shop
