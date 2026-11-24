package shop

// names that are not the type of their name
class Inherit : Order(1) {
    fun inherited(): Any {
        val a = Line()   //> Line=shop.Order.Line/r
        val b = Tools.go()   //> Tools=shop.Order.Tools/r
        val c = create()   //> create=function/r
        val d = Empty   //> Empty=property/r
        val e = Member()   //> Member=function/r
        return listOf(a, b, c, d, e)   //> listOf=function/r a=var/r b=var/r c=var/r d=var/r e=var/r
    }
}

class Shadow(val Customer: Int) {
    val Money = 2
    fun shadowed(Order: String): Any {
        val Registry = 3
        val a = Customer.plus(1)   //> Customer=property/r
        val b = Money.plus(1)   //> Money=property/r
        val c = Order.length   //> Order=var/r
        val d = Registry.plus(1)   //> Registry=var/r
        val e = listOf(1).map { Status -> Status + 1 }   //> listOf=function/r Status=- Status=var/r
        return listOf(a, b, c, d, e)   //> listOf=function/r a=var/r b=var/r c=var/r d=var/r e=var/r
    }
}

class Builder { fun Widget(): Int = 0; val Plugin = 1 }
fun build(b: Builder.() -> Unit) {}

class Receivers {
    fun lambdas(): Any {
        build { Widget(); Plugin }   //> build=function/r Widget=function/r Plugin=property/r
        return with(Money(1)) { v }   //> with=function/r Money=shop.Money/r v=property/r
    }
    fun labels(): Any = listOf(1).map { this@Receivers }   //> listOf=function/r Receivers=label/r
    fun named(): Any = Order(id = 1)   //> Order=shop.Order/r id=-
}
