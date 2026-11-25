#include "app/types.h"
namespace app {
namespace { struct Local { int v = 0; }; }
Money Order::zero = Money(0);
Order::Order() : m_(Money(2)) {}
int Order::tryit() const {
  try { throw lib::Oops(); } catch (const lib::Oops& e) { (void)e; }
  Local l;
  Thing items[2];
  for (const Thing& it : items) { (void)it; }
  Money t;
  return l.v + sizeof(t);
}
}
