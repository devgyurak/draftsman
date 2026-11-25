package q

import p.*
import p.Money as Coin

class Money

class Holder2(val a: Money, val b: Coin, val c: Other) {
    fun f(): Any = Money()
}
