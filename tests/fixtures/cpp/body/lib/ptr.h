#pragma once

namespace lib {

template <class C>
class AutoPtr {
 public:
  explicit AutoPtr(C* p = nullptr) : p_(p) {}
  C* get() const { return p_; }

 private:
  C* p_;
};

class Channel {
 public:
  typedef AutoPtr<Channel> Ptr;
  virtual ~Channel() {}
};

}  // namespace lib
