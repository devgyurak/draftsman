#include "fw/api.h"
namespace fw {
#ifdef _WIN32
class Impl { void* h; };
#else
class Impl { int fd; };
#endif
}
