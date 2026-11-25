package q

import p.*
import p.Money as Coin
import r.*

// #9: `Money` is not p.Money through `import p.*` once p.Money is imported as Coin;
// r.Money through `import r.*`
class Holder2(val a: Money, val b: Coin) {
    fun f(x: Money): Coin? = null
    fun g(): Any = Money()
}
