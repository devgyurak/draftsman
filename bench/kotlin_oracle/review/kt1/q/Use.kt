package q

import p.*
import p.Dup
import p.State.Loading

class Derived : Base(Money(1).v), Iface {
    val lazyM by lazy { Money(1) }
    fun inherited(): Any {
        val a = Inner()
        val t = Tools.go()
        val m = make()
        val z = Zero
        val f = Member()
        return listOf(a, t, m, z, f)
    }
    fun calls(x: Any, s: State): Any {
        val a = Money(1)
        val b = Money("s")
        val c = Money(1, 2)
        val e = Widget()
        val f = Widget(1)
        val g = Cash(1)
        val h: Cash = g
        val i = Action { }
        val j = Plugin
        val k = listOf(Registry, Color.Red, Color.Default, Color)
        val l = when (s) { Loading -> 1; is State.Done -> 2 }
        val m = x is Money || x as? Base != null
        val n = listOf(Money::class, Base.Inner::class, ::Money, Money::v, p.Money(1), p.Registry.all)
        val o = "${Registry.all} $Plugin ${this@Derived} ${super<Base>.toString()}"
        val p1 = listOf<Money>() + emptyMap<String, Base.Inner>().keys
        val q1: Result? = null
        val r = Dup()
        val s1 = Sibling()
        val t: @Mark Money? = null
        fun loc(vararg ms: Money, d: Money = Money(0)) {}
        try { } catch (e: MyErr) { }
        class Local : Base(2) { fun g() = Money(1) }
        val u = object : Iface { fun h() = Widget() }
        with(Money(1)) { v }
        dsl { Widget(); Registry }
        return 0
    }
    companion object { fun mk() = Money(1) }
    object Named { fun mk() = Money(1) }
}

fun top() = Money(1)
val topVal = Widget()
fun Base.ext() = Member()
