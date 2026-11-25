#include "app/types.h"
namespace app {
struct User : Base {
  Money m_;
  Money pay(const Money& a);
  Inner i_;
};
}
namespace other {
struct O {
  Money m_;
  Base b_;
};
}
