package shop

import shop.Status.Paid
import shop.Order.Companion.create
import shop.Cash as Coin

class Aliases {
    fun f(x: Any): Any {
        val a: Handler = { }
        val b: Cashes = listOf()
        val c = Gen<Int>(1)
        val d = Err("x")
        val e = x is Err
        val g = Cash2(1)
        val h: Cash2? = null
        val i = Line2()
        val j = Coin(1)
        val k = Cash("s")
        val l = Cash::class
        val m = Cash.Zero
        val n = Gen<Money>(Money(1))
        return listOf(a, b, c, d, e, g, h, i, j, k, l, m, n)
    }
}

class Companions {
    fun f(o: Order): Any {
        val a = Order.Companion.create()
        val b = Order.Companion
        val c = Order.Companion.Ser()
        val d = Money.Named.Zero
        val e = Money.Named
        val g = Ticket.Factory.run()
        val h = Ticket
        val i = o.Part()
        val j = Order.Companion::create
        val k = Order::Part
        val l = Order.Line::class
        val m = Registry(3)
        val n = create()
        val p = Paid
        val q = Status.valueOf("New")
        val r = enumValues<Status>()
        val s = Holder.Nested()
        return listOf(a, b, c, d, e, g, h, i, j, k, l, m, n, p, q, r, s)
    }
}

class Nesting {
    class Inner { fun f() = Money(1) }
    object Obj { fun f() = Money(2) }
    interface Face { fun f(): Any = Money(3) }
    companion object { class InComp { fun f() = Money(4) } }
    private val prop = object : Order(Money(5).v), Holder { val q = Money(6); override fun describe() = super<Order>.describe() + super<Holder>.hold() + this@Nesting }
    var acc: Int
        get() = Money(7).v
        set(value) { Registry.all }
    constructor(m: Money) : this() { Money(8) }
    constructor()
    fun Money.twice() = Money(v * 2)
}

class Delegating(a: Action) : Action by a
class Delegating2 : Action by Action({ Money(9) })

class Forms {
    fun f(list: List<Money>, x: Any): Any {
        for (m: Money in list) { }
        val a = { m: Money -> m.v }
        val b = fun(m: Money): Order = Order(m.v)
        val c: (Money) -> Order = { Order(it.v) }
        val d: Map<String, List<Money?>>? = null
        val e = Box<Money>(Money(1))
        val g = x is Box<*>
        val h = Array<Money>::class
        val i: shop.Money = shop.Money(1)
        val j = shop.Order.Line()
        val k = `Money`(1)
        fun <T : Money> loc(t: T): T where T : Any = t
        @Anno(Customer::class) val l = 1
        val m = when (x) { is Money -> 1; Registry -> 2; Paid -> 3; else -> 4 }
        val n = when (val s = Status.New) { Status.Paid -> 1; else -> 2 }
        val o = "$Registry ${Money(1).v} $x"
        val p = if (x is Money) x.v else (x as Order).id
        val q = Money::class.java
        val r = listOf(Money(1), *arrayOf(Money(2)))
        val s = lib.Outside()
        return listOf(a, b, c, d, e, g, h, i, j, k, l, m, n, o, p, q, r, s)
    }
}

fun Money.double() = Money(v * 2)
val topObj = object : Action { override fun run() { Money(1) } }
