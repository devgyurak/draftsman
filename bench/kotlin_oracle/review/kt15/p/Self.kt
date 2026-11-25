package p

import p.Money as Coin
import r.*

// #9: once a file imports p.Money under another name, `Money` is not p.Money through the
// file's own package: here it is r.Money, through the star import
class Same(val a: Money, val b: Coin) {
    fun f(x: Money): Coin? = null
    fun g(): Any = Money()
}
