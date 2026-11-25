package q

import p.Money
import p.Money as Coin
import p.Outer.In as PIn

class Both(val a: Money, val b: Coin, val c: PIn) {
    fun f(): Any = Money()
}
