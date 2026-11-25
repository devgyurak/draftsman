#pragma once
// #19: a dependent base is not looked into; a base of a known argument is
namespace c19 {
struct Inner {};
template <class T> struct TBase { struct Inner {}; };
template <class T> struct Vec : TBase<T> {
  Inner i;
  void put(Inner x);
};
struct Fixed : TBase<int> {
  Inner j;
};
}
