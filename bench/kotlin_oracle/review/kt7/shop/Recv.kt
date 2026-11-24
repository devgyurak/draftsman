package shop

class R {
    fun f(c: Ctx) = with(c) { Money(1) }
    fun g(c: Ctx) = c.run { Order.toString() }
    fun Ctx.ext() = Money(2)
    fun Ctx.ext2() = Order.toString()
    val Ctx.prop: Int get() = Money(3)
    fun h() = Money(4)
}
