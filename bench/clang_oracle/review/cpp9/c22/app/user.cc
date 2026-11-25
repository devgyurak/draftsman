#include "c22/app/types.h"
namespace app {
struct User {
  Money m;
  Money pay(const Money& x);
};
}
