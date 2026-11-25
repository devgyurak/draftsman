#pragma once
#include "g.h"
namespace shop {
struct Inner {};
struct Helper {};
template <class T> struct TBase { struct Inner {}; int Helper; };
template <class T> struct Mid : TBase<T> {};
template <class T> struct Top : Mid<int> {
  int g() { Inner i; return sizeof(i); }
};
template <class T> struct Top2 : Mid<T> {
  int g() { Inner i; Helper h; return sizeof(i) + sizeof(h); }
};
template <class T> struct Q : TBase<T> {
  template <class U> int g(U) { Inner i; return sizeof(i); }
};
template <class T> struct R : TBase<int>, Mid<T> {
  int g() { Inner i; return sizeof(i); }
};
template <class T> struct Outer2 : TBase<T> {
  struct In {
    int g() { Helper h; Inner i; return sizeof(h) + sizeof(i); }
  };
};
struct Outer3 : TBase<int> {
  struct In {
    int g() { Inner i; return sizeof(i) + sizeof(Helper); }
  };
};
}
