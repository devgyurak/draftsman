#pragma once
#define API
namespace app {
class API Fwd2;
template <class T, class U = int> class Fwd3;
struct Friendly { friend class Util; int f(); };
}
