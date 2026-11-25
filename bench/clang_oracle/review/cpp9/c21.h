#pragma once
// #21: a namespace alias of the file; a nearer namespace of the name wins
namespace a21 { namespace inner { struct E {}; } }
namespace gs = a21::inner;
namespace c21 {
namespace gs { struct E {}; }
struct Near { gs::E e; };
}
struct Far { gs::E e; gs::E take(gs::E x); };
