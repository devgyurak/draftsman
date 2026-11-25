#pragma once
#include <map>
// #15: an alias template's own parameter `Hash` is no type
namespace c15 {
struct Hash {};
template <class K, class Hash = int> using Table = std::map<K, Hash>;
struct Store {
  Table<int> t;
  void put(Table<int> x);
};
}
