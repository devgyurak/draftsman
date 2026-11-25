#pragma once
// #16: the head of `Mutex::ScopedLock` is the class's own alias Mutex
namespace c16 {
template <class M> struct Lock {};
struct FastMutex { using ScopedLock = Lock<FastMutex>; };
struct Mutex { using ScopedLock = Lock<Mutex>; };
struct Poller {
  using Mutex = FastMutex;
  Mutex::ScopedLock l;
  void hold(Mutex::ScopedLock& x);
};
}
