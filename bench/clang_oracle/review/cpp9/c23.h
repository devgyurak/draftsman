#pragma once
// #23: a nearer namespace's type comes before a using declaration of an outer one
namespace lib23 { struct Coin {}; }
namespace app23 { using lib23::Coin; }
namespace app23 { namespace in {
struct Coin {};
struct W {
  Coin c;
  Coin give(Coin x);
};
} }
