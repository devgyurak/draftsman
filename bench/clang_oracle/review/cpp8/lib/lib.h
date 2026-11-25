#pragma once
namespace lib {
struct Money { Money(int = 0) {} };
struct Item {};
using Thing = Item;
struct Stamp {};
struct Coin {};
template <class T> struct Box {};
int Make(int);
extern int Limit;
}
namespace lib2 { struct Money { Money(int = 0) {} }; }
