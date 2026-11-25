#pragma once
#include "g.h"
namespace shop3 {
struct Keeper {
  State st_;
  State get(const State& s);
};
}
