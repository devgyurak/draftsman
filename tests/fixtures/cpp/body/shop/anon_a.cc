#include "shop/keeper.h"

namespace shop {
namespace {
struct State {
  int a = 0;
};
}  // namespace

int useA() {
  State s;  //> State=shop::State/t
  return s.a;
}

int Keeper::fromA() const {  //> Keeper=-
  State s;  //> State=shop::State/t
  return s.a;
}

}  // namespace shop
