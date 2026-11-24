#include "shop/model.h"
#include <typeinfo>
#include <cstddef>
#define STR(x) #x
#define ID(x) x
#define DECL(T, n) T n
#define NEWOF(T) new T
#define SIZE(T) sizeof(T)
#define FEATURE 1

namespace shop {

int Maker(int x) { return x; }

#if FEATURE
struct Gate { int s; };                  // shop::Gate, in a branch that is taken
#endif
#ifdef NOT_DEFINED
struct Opt { int s; };                   // shop::Opt, in a branch that is not taken
#endif

class Work {
 public:
  int Tag = 0;
  int macros() {
    const char* a = STR(Money::Zero);        // no name
    const char* b = STR(shop::Money);        // no name
    Money m = ID(Money::Zero());             // shop::Money x2
    DECL(Money, d);                          // shop::Money
    Money* p = NEWOF(Money);                 // shop::Money x2
    return m.v + d.v + p->v + SIZE(Money) + (a != b);
  }
  int vexing() {
    Lock l1(Tag);                            // the field Tag
    Lock l2(Paid);                           // the enumerator shop::Paid
    Lock l3(Money);                          // a function declaration: l3 takes a shop::Money
    Lock l4(Money(1));                       // a function declaration again: l4 takes a Money named 1? no: see Clang
    (void)l1, (void)l2;
    return sizeof(Paid) + (typeid(Paid) == typeid(int));
  }
  int calls() {
    int a = Maker(1);                        // the function shop::Maker
    Feed f = Feed(2);                        // shop::Feed
    FeedPtr fp = FeedPtr(&f);                // the alias: lib::AutoPtr, shop::Feed
    Cash c = Cash(3);                        // the alias: shop::Money
    Chan ch;                                 // the alias: lib::AutoPtr (through Ref), lib::Channel
    lib::Channel::Ptr cp;                    // lib::Channel, then its alias
    lib::Ref<Feed> rf;                       // the alias template: lib::AutoPtr; shop::Feed
    lib::Versioned v{4};                     // lib::v1::Versioned
    deep::Nested n{5};                       // shop::deep::Nested
    ::Tag gt{6};                             // ::Tag
    ::Money gm{7};                           // ::Money
    return a + f.s + (fp.get() != nullptr) + c.v + (ch.get() == cp.get()) + (rf.get() == nullptr) + v.v + n.n + gt.g + gm.g;
  }
  int branches() {
    Gate g{1};                               // shop::Gate
    Opt o{2};                                // ::Opt: shop::Opt is not compiled
#if FEATURE
    Gate g2{3};                              // shop::Gate
    return g.s + o.g + g2.s;
#else
    return 0;
#endif
  }
  int exprs(const void* q) {
    const Money* m = static_cast<const Money*>(q);                 // shop::Money x2
    auto f = [](const Feed& x) -> Money { return Money(x.s); };   // shop::Feed, shop::Money x2
    int Work::*pm = &Work::Tag;                                    // shop::Work x2
    decltype(Money(1)) dm;                                         // shop::Money
    static_assert(sizeof(Feed) > 0, "x");                          // shop::Feed
    return m->v + f(Feed(1)).v + this->*pm + dm.v + alignof(Money) + offsetof(Feed, s) + noexcept(Money(1));
  }
  friend int peek(const Work& w) { Money m{w.Tag}; return m.v; }   // shop::Money, the class's
  int dflt(Money m = Money(1), int k = sizeof(Feed)) { return m.v + k; }   // shop::Money (default argument), shop::Feed
  Money held = Money(2);                                           // shop::Money (default member initializer)
};

}  // namespace shop

namespace n1 { using namespace lib; }
namespace n2 {
struct Channel { int n2; };
struct K { int f() { Channel c{1}; return c.n2; } };   // n2::Channel
}
struct G { int f() { Feed c{1}; return c.g; } };       // ::Feed
