#pragma once
#include "g.h"
#include "lib/lib.h"
namespace app {
using lib::Money;
using lib::Thing;
using lib::Box;
using lib::Make;
using lib::Limit;
namespace detail { struct Impl {}; }
using detail::Impl;
namespace in { struct Money { Money(int = 0) {} }; }
}
namespace shop { using lib2::Money; }
namespace far { using namespace lib; }
