package shop

class Acc {
    val Ctx.p: Any
        get() = Money(3)
    var Ctx.q: Int
        get() = Order
        set(v) { println(Registry) }
    val r: Any
        // a comment between
        get() = Money(4)
    val s: Int = 1
    val t: Any
        get() {
            val Money = 5
            return Money
        }
    val u: Any
        get() = Money.ZERO
    @Suppress("unused")
    val v: Any get() = Registry
    val w: Any by lazy { Order.create() }
    var x: Any = Registry
        private set
    var y: Any = Money.ZERO
        get() = field
        set(value) { field = Order.create() }
}
class Rc {
    fun T2.a(): Any = name.length
    fun shop.Ctx.b() = Money(2)
    fun LC.c() = Money(2)
    val d = fun Ctx.(): Int = Money(2)
    val e: Ctx.() -> Int = { Money(1) }
    fun f(): Any = fun Ctx.(): Any = Order
    fun Ctx.Part.g() = Money(2)
    fun (Ctx).h() = Money(2)
    fun @receiver:Suppress("x") Ctx.i() = Money(2)
}
class Bx<T : Ctx, U : T, V> {
    fun T.a() = Money(1)
    fun U.b() = Money(1)
    fun V.c() = Money(1)
    fun <W : T> W.d() = Money(1)
    fun <X : Thread> X.e(): Any = name.length
}
