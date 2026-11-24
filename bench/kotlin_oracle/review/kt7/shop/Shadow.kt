package shop

enum class Mode { Money, Other;
    fun f() = Money.name
    fun g(): Any = shop.Money(1)
}
class Shadow {
    class Money(val s: String)
    fun f() = Money("s")
    fun g() = shop.Money(1)
    fun h() { val m: Money? = null; println(m) }
}
class Shadow2 { val Money = 5; fun f() = Money.toString(); fun g() { val m: Money? = null; println(m) } }
class Shadow3 { object Registry { val q = 1 }; fun f() = Registry.q }
class Shadow4 {
    companion object { val Registry = 1; class Kind }
    fun f() = Registry.toString()
    fun g() { val k: Kind? = null; println(k) }
}
class Shadow5 { fun Registry() = 1; fun f() = Registry.size; fun g() = Registry() }
class Loc {
    fun f(): Any { run { val Money = 3; println(Money) }; return Order() }
    fun f2(): Any { run { val Money = 3; println(Money) }; return Money(1) }
    fun g(): Any { val q = Money.ZERO; class Money; return q }
    fun h(items: List<Int>) { for (Money in items) println(Money); items.forEach { Order -> println(Order) }
        val (Kind, Registry) = Pair(1, 2); println(Kind + Registry) }
    fun i() { try { } catch (Money: Exception) { Money.printStackTrace() } }
    fun j(x: Any) { when (val Order = x) { is Money -> println(Order); else -> { } } }
    fun k() = Registry.find()
}
