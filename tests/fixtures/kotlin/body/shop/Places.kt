package shop

// the places a body is: initializers, getters, delegation, init, default arguments,
// a superclass's constructor arguments, an enum entry's arguments, local functions
class Places(val first: Order = Order(5)) : Order(Status.New.code) {   //> Order=- Order=shop.Order/r Order=- Status=shop.Status/r
    val second = Customer("p")   //> Customer=shop.Customer/r
    val third: Customer get() = Customer("q")   //> Customer=- Customer=shop.Customer/r
    val fourth by lazy { Money(4) }   //> lazy=function/r Money=shop.Money/r

    init {
        Registry.all   //> Registry=shop.Registry/r
    }

    fun local(): Any {
        fun inner(vararg ms: Money, d: Money = Money(0)) = ms.size + d.v   //> Money=shop.Money/t Money=shop.Money/t Money=shop.Money/r ms=- ms=var/r d=- d=var/r
        return inner()   //> inner=function/r
    }

    fun nested(): Any {
        class Local : Order(7) { fun g() = Customer("l") }   //> Order=shop.Order/t Customer=shop.Customer/r
        val o = object : Action { override fun run() { Money(8) } }   //> Action=shop.Action/t Money=shop.Money/r
        return listOf(Local(), o)   //> listOf=function/r Local=local/r o=var/r
    }

    companion object {
        fun make() = Customer("c")   //> Customer=shop.Customer/r
    }
}

enum class Kind(val m: Money) {
    Big(Money(100)) { override fun f() = Customer("b") },   //> Money=shop.Money/r Customer=shop.Customer/r
    Small(Money(1));   //> Money=shop.Money/r
    open fun f(): Any = 0
}

// code outside every type
fun top(): Any = Customer("t")   //> Customer=shop.Customer/r
val topValue = Order(9)   //> Order=shop.Order/r
