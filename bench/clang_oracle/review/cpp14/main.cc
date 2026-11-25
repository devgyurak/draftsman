#include "supers.h"

int main() {
  a::Holder h;
  a::Holder2 h2;
  return static_cast<int>(h.items_.size() + h2.m_.size());
}
