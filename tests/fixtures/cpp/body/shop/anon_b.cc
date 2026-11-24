#include "shop/keeper.h"

namespace shop {
namespace {
struct State {
  int b = 0;
};
}  // namespace

int useB() {
  State s;  //> State=shop::State/t
  return s.b;
}

}  // namespace shop
