#pragma once
struct Inner {};
struct Base {};
struct Handle {};
struct Paid {};
struct Impl {};
struct Sel;
#ifdef WIDE
struct Sel { long v; };
#endif
