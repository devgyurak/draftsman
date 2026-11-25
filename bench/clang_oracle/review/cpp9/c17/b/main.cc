#include "gen.h"
using namespace gen;
struct ToolB {
  Utility u;
  Utility make(const Utility& from);
};
int main() { ToolB t; return t.u.b; }
