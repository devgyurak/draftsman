#pragma once
#include "g.h"
namespace ch {
#if defined(_WIN32)
struct Sock { struct Handle { void* h; }; };
#elif defined(__APPLE__)
struct Sock { struct Handle { int kq; }; };
#else
struct Sock { struct Handle { int fd; }; };
#endif
struct Conn : Sock {
  Handle h_;
  Sock* peer_;
};
#if defined(_WIN32)
struct Impl { void* h; };
#elif defined(__linux__) || defined(__APPLE__)
struct Impl { int fd; };
#else
#error "unsupported"
#endif
struct Api {
  Impl* p_;
};
#ifdef _WIN32
#ifdef UNICODE
struct Str { wchar_t* w; };
#else
struct Str { char* a; };
#endif
#else
struct Str { char* u; };
#endif
struct Text {
  Str s_;
};
#ifdef _WIN32
struct Fwd;
#else
struct Fwd { int x; };
#endif
struct UsesFwd {
  Fwd* f_;
};
}
