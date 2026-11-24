// included by app/use.cc after app/late.h: no include of its own
namespace app {
struct Impl {
  int run() { Late l{1}; return l.a; }   // app::Late: the including file has it by then
};
}
