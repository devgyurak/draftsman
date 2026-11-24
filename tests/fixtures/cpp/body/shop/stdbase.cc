#include <time.h>

#include <ostream>
#include <vector>

namespace shop {

struct Init {};
struct precision {
  explicit precision(int) {}
};
struct reference {};

// a base class of std hides a name by a member: std::ios_base's Init and precision()
class Stream : public std::ostream {
 public:
  Stream() : std::ostream(nullptr) {}
  void f() {
    Init i;  //> Init=std::ios_base::Init/t
    precision(3);  //> precision=method/r
    (void)i;
  }
};

// a base the table does not know (a C struct) hides nothing
struct Stamp : tm {
  void f() {
    Init i;  //> Init=shop::Init/t
    (void)i;
  }
};

// nor does a base written with the class's template parameter: it is looked into once T
// is known
template <class T>
struct Vec : std::vector<T> {
  void f() {
    reference r;  //> reference=shop::reference/t
    (void)r;
  }
};

}  // namespace shop
