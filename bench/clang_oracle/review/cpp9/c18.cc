#include <sys/time.h>
// #18: a type of an `#if` branch not taken, beside the system's
#ifdef OLD_TIMEVAL
struct timeval { long s; };
#endif
struct Clock {
  timeval tv;
  void set(const timeval& t);
};
