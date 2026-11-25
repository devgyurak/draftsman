#pragma once
namespace fw {
struct Impl;
struct Holder {
  Impl* p_;
  Impl* get();
  struct Pim;
  Pim* q_;
};
}
