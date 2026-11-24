package q

import other.Widget
import other.make as Money
import shop.Kind.A
import shop.Order.Part
import shop.Registry.find
import shop.Money.Companion.ZERO
import shop.Gadget as G

class D {
    fun a() = Widget(1)
    fun b() = Money(1)
    fun c() = A.name
    fun d() = Part()
    fun e() = find()
    fun f() = ZERO.amount
    fun g() = G.x
    fun h() { val p: Part? = null; val g: G? = null; println("$p $g") }
}
