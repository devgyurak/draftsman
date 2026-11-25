#pragma once
#include <map>
#include <memory>
#include <vector>
#include "lib/lib.h"
namespace sig {
struct Key {};
struct Item {};
struct Repo {
  std::map<Key, std::vector<Item>> all_;
  std::shared_ptr<lib::Money> find(const Key& k, Item* out);
  static Repo* instance();
  std::vector<lib::Box<Money>> boxes_;
  std::vector<Item>::size_type n_;
};
}
