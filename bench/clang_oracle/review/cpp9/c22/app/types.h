#pragma once
#include "c22/money.h"
// #22: a header's using declaration is a name of its namespace where it is included
namespace lib { struct Money {}; }
namespace app { using lib::Money; }
