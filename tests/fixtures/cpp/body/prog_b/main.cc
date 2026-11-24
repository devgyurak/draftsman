#include "gen/codegen.h"

using namespace gen;

// prog_a's Utility is another program's: this file includes none of it
struct Generator {
  int go() { return Utility::run(); }  //> Utility=gen::Utility/t
};
