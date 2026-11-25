#include "nested.h"
namespace own {
struct Table::Rep { int n; };
Table::Table(Rep* r) : rep_(r) {}
}
