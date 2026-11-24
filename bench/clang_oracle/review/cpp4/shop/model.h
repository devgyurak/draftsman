#pragma once
struct Money { int g; };                 // ::Money
struct Tag { int g; };                   // ::Tag
struct Paid { int g; };                  // ::Paid
struct Maker { int g; };                 // ::Maker
struct Feed { int g; };                  // ::Feed
struct Gate { int g; };                  // ::Gate
struct Opt { int g; };                   // ::Opt
namespace lib {
template <class T> struct AutoPtr { T* p; AutoPtr(T* q = nullptr) : p(q) {} T* get() const { return p; } };
template <class T> using Ref = AutoPtr<T>;
struct Channel { typedef AutoPtr<Channel> Ptr; int l; };
inline namespace v1 { struct Versioned { int v; }; }
}
namespace shop::deep { struct Nested { int n; }; }
namespace shop {
enum Kind { Paid, Open };                // shop::Paid is an enumerator
struct Money { int v; Money(int x = 0) : v(x) {} static const char* kName; static Money Zero(); };
struct Tag { int s; };
struct Lock { Lock(int) {} Lock(Tag) {} Lock(Money) {} };
int Maker(int x);                        // a function named like ::Maker
struct Feed { int s; Feed(int x = 0) : s(x) {} };
typedef lib::AutoPtr<Feed> FeedPtr;
typedef Money Cash;
using Chan = lib::Ref<lib::Channel>;
}
