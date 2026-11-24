package shop

open class Taker(val x: Any)
enum class Mode2(val v: Any) { Money(Registry), Other(Kind.A);
    fun f(): Any = Money
    fun g(): Any = listOf(Money, Other)
}
class Sub3 : Base() {
    fun a(): Any = Flag
    fun b(): Any = Prop
    fun c(): Any = listOf(Flag, Prop, Nested)
    fun d(): Any = Nested
}
class Impl3 : Face2 {
    fun a(): Any = Flag2
    fun b(): Any = Helper2()
}
class Z(val p: Any = Registry) : Taker(Registry), Face by Proxy {
    val q: Any = Registry
    val r: Any by lazy { Registry }
    init { println(Registry) }
    fun a(): Any = if (p == q) Registry else Money
    fun b(x: Any): Boolean = x == Registry || x === Money || x in listOf(Registry)
    fun c(): Any = Registry to Money
    fun d(): Any = (Registry as Any?) ?: Money
    fun e(): Any = arrayOf(Registry, Money)[0]
    fun f(): Any { var v: Any = Registry; v = Money; return v }
    fun g(): Any = run { Registry }
    fun h(): Any = Registry.let { it }
    fun i(): Any = "${Registry} $Money"
    fun j(x: Any = Registry): Any = x
    fun k(): Any { throw IllegalStateException(Registry.toString()) }
    fun l(x: Any): Any = when (x) { Registry -> Money; is Order -> Order; else -> Kind.A }
    fun m(): Any = Order.Companion
    fun n(): Any = Money.Companion.ZERO
    fun o(): Any = shop.Registry
    fun s(): Any = Registry::class
    fun v(vararg x: Any): Any = v(*arrayOf(Registry))
    fun w(): Any = listOf(Kind.A, Kind.B).map { Money }
    fun y(): Any { val t = Registry; return t }
}
object Proxy : Face
