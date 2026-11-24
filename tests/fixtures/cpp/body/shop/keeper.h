#pragma once

#include "shop/model.h"

namespace shop {

// no State of its own namespace here: the global one
struct Keeper {
  int fromA() const;
  int fromHere() const {
    State st;  //> State=State/t
    return sizeof(st);
  }
};

}  // namespace shop
