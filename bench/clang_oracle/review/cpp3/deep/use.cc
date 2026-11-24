#include "g.h"
#include "sub/deep.h"             // sub/deep.h of the include path: one/sub/deep.h is not included
#include "one/util.h"
namespace app {
struct D2 {
  int f() {
    Deep d{1};                    // ::Deep
    Util u{2};                    // app::Util
    return d.g + u.one;
  }
};
}
