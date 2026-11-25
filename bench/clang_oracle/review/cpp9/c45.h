#pragma once
#include <utility>
#include <vector>
// #45: an alias of a member of an outside template names none of its arguments;
// `typename std::pair<K, V>` is the pair
namespace c45 {
struct Item {};
struct Var {};
struct Holder {
  typedef std::vector<Item>::const_iterator ConstIterator;
  bool first(ConstIterator& it) const;
};
template <class K> struct Pair {
  using Data = typename std::pair<K, Var>;
  Data d;
};
}
