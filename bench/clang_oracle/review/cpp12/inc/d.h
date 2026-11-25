namespace inc {
struct D : B {
  Inner i_;
  int f() { Inner x; return sizeof(x); }
};
}
