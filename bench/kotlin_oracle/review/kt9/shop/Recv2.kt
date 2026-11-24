package shop

typealias C2 = Ctx
class Sub2 : Base()
class name { companion object { val x = 1 } }
open class Worker2 : Thread() {
    fun f(): Any = name.length
    fun g(): Any = name
}
class Worker3 : Worker2() {
    fun f2(): Any = name.length
}
class R2 {
    fun <T : Ctx> T.a() = Money(2)
    fun C2.b() = Money(2)
    fun Ctx?.c() = Money(2)
    fun List<Ctx>.d() = Money(2)
    fun Ctx.e(): Any = object : Face { fun g() = Money(1) }
    fun Ctx.f(): Any {
        class L { fun g() = Order.toString() }
        return L()
    }
    fun g(): Any {
        fun Ctx.loc() = Money(5)
        return Ctx().loc() + Money(6).amount
    }
    val Ctx.p: Any get() = Order
    fun Sub2.h() = Tool()
    fun Sub2.i(): Any = Prop
    fun Sub2.j(): Any = Nested()
    fun Sub2.k(): Any = Flag
    fun Thread.l(): Any = name.length
    fun Worker2.m(): Any = name.length
    fun <T : Thread> T.n(): Any = name.length
    fun <T> T.o(): Any where T : Ctx = Order
}
