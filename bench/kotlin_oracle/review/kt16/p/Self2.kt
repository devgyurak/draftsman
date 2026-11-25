package p

import p.Money as Coin
import r.*

class Keeper(val a: Money, val b: Coin, val c: p.Money) {
    fun f(): Any = Money()
    val o: Other? = null
}

open class HasNested { class Money }

class Sub3(val a: Money) : HasNested() {
    fun f(x: Money): Any = Money()
}
