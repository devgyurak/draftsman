#pragma once
#include "g.h"
namespace shop {
struct Inner {};
struct Helper {};
template <class T> struct TBase { struct Inner {}; int Helper; struct Deep {}; };
struct Plain { struct Inner {}; };
template <class T> struct Box2 {};

template <class T> struct Outer {
  struct In : TBase<T> {
    int g() { Inner i; Helper h; return sizeof(i) + sizeof(h); }
  };
};
template <class T> struct ViaPtr : TBase<T*> {
  int g() { Inner i; return sizeof(i); }
};
template <class T> struct ViaBox : TBase<Box2<T>> {
  int g() { Inner i; return sizeof(i); }
};
template <class B> struct Mix : B {
  int g() { Inner i; return sizeof(i); }
};
template <class... Ts> struct Var : TBase<Ts...> {
  int g() { Inner i; return sizeof(i); }
};
template <int N> struct NBase { struct Inner {}; };
template <int N> struct Arr : NBase<N> {
  int g() { Inner i; return sizeof(i); }
};
template <class T> struct Solid : Plain {
  int g() { Inner i; return sizeof(i); }
};
template <class T> struct Two : Plain, TBase<T> {
  int g() { Inner i; return sizeof(i); }
};
struct Fixed : TBase<int> {
  template <class U> int g(U) { Inner i; return sizeof(i); }
};
template <class T> struct Chain : ViaPtr<int> {
  int g() { Inner i; return sizeof(i); }
};
struct Leaf : ViaPtr<int> {
  int g() { Inner i; Deep d; return sizeof(i) + sizeof(d); }
  int h() { return sizeof(Helper); }
};
}
