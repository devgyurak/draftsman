#pragma once
// #20: `::D` is the global namespace's
struct D {};
namespace c20 {
struct D {};
struct Y {
  ::D g;
  ::D get() const;
  D h;
};
}
