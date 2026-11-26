#pragma once
#include <map>
#include <vector>
namespace c16 {
struct Item {};
struct Money {};
struct Handler {};
struct Order {};
struct Iterator {};   // a rival of SkipList's nested Iterator
template <class K> struct SkipList { struct Iterator { K k; }; };
// 43: conversion operators name their type
struct Conv {
  operator const Item&() const;
  explicit operator bool() const;
  operator Money() const;
};
// 44: an abstract pointer to a function in an alias; a typedef returning a pointer; a member
// pointer written directly names its class, one in an alias does not (Clang's key)
struct Engine {
  using Gen = void (*)(const Item*, Order& order);
  using Start = void (Handler::*)(const Item&);
  typedef Money* (*Make)(const Order&);
  Gen gen_;
  Start start_;
  Make make_;
  void (Order::*direct_)(int);
};
// 47: a member of an alias of a template specialisation, through a class
struct Table2 {
  typedef SkipList<int> Table;
  Table::Iterator it_;
};
struct User2 { Table2::Table::Iterator it_; };
// an assignment operator does not make an interface a class
struct Face {
  virtual ~Face();
  virtual void run() = 0;
  Face& operator=(const Face&);
};
struct Impl : Face { void run() override {} };
}  // namespace c16
