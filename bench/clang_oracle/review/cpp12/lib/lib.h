#pragma once
#include "g.h"
namespace lib {
struct Base { struct Inner {}; };
struct EBase { enum Kind { Paid, Open }; };
}
