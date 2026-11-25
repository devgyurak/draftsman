#pragma once
#include "types.h"

namespace a {
struct NodeList : std::vector<Node> {};
template <class T> struct Gen : std::vector<T> {};
struct Nested : std::map<int, std::vector<Item>> {};
struct UsesB : std::vector<b::Node> {};
struct Sub : Base<Item> {};
template <class T> struct GenSub : Base<std::vector<T>> {};

struct Holder {
  typedef std::vector<Item> Vector;
  Vector items_;
};

struct Holder2 {
  using Map = std::map<int, Node>;
  Map m_;
};
}  // namespace a
