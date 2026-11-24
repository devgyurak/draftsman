package shop

import lib.Picked
import lib.Order as LibOrder

// a name that only a type can be, and a name a value can be as well
class Uses(val customer: Customer) {
    fun types(x: Any): Any {
        val a: Order? = null   //> Order=shop.Order/t
        val b = x is Customer   //> x=var/r Customer=shop.Customer/t
        val c = x as? Money   //> x=var/r Money=shop.Money/t
        val d = listOf<Customer>()   //> listOf=function/r Customer=shop.Customer/t
        val e: Order.Line? = null   //> Order=shop.Order/t Line=shop.Order.Line/t
        val f: @Mark Customer? = null   //> Mark=shop.Mark/t Customer=shop.Customer/t
        try { } catch (p: Problem) { }   //> Problem=shop.Problem/t
        return listOf(a, b, c, d, e, f)   //> listOf=function/r a=var/r b=var/r c=var/r d=var/r e=var/r f=var/r
    }

    fun values(): Any {
        val a = Order(1)   //> Order=shop.Order/r
        val b = Order.Line()   //> Order=shop.Order/r Line=shop.Order.Line/r
        val c = Order.create()   //> Order=shop.Order/r
        val d = Order.Empty   //> Order=shop.Order/r
        val e = Order.Tools.go()   //> Order=shop.Order/r Tools=shop.Order.Tools/r
        val f = Registry.all   //> Registry=shop.Registry/r
        val g = Status.Paid   //> Status=shop.Status/r
        val h = Cash(2)   //> Cash=shop.Money/r
        val i = Action { }   //> Action=shop.Action/r
        val j = listOf(Registry, Status.New, Order)   //> listOf=function/r Registry=shop.Registry/r Status=shop.Status/r Order=shop.Order/r
        val k = Customer::class   //> Customer=shop.Customer/r
        val l = Customer::name   //> Customer=shop.Customer/r
        val m = ::Customer   //> Customer=shop.Customer/r
        val n = shop.Order(2)   //> shop=package/r Order=shop.Order/r
        return listOf(a, b, c, d, e, f, g, h, i, j, k, l, m, n)   //> listOf=function/r a=var/r b=var/r c=var/r d=var/r e=var/r f=var/r g=var/r h=var/r i=var/r j=var/r k=var/r l=var/r m=var/r n=var/r
    }

    fun sameName(): Any {
        val a = Money(1)   //> Money=shop.Money/r
        val b = Money(1, 2)   //> Money=function/r
        val c = Money("s")   //> Money=shop.Money/r
        val d = Plugin   //> Plugin=property/r
        val e = Widget()   //> Widget=function/r
        return listOf(a, b, c, d, e)   //> listOf=function/r a=var/r b=var/r c=var/r d=var/r e=var/r
    }

    fun imports(): Any {
        val a = Picked()   //> Picked=lib.Picked/r
        val b = LibOrder()   //> LibOrder=lib.Order/r
        val c = Result()   //> Result=shop.Result/r
        val d = engines()   //> engines=shop.engines/r
        val e = Ticket.Factory   //> Ticket=shop.Ticket/r Factory=shop.Ticket.Factory/r
        return listOf(a, b, c, d, e)   //> listOf=function/r a=var/r b=var/r c=var/r d=var/r e=var/r
    }

    fun text(): String = "${Registry.all} ${Plugin} ${this@Uses} ${customer.name}"   //> Registry=shop.Registry/r Plugin=property/r Uses=label/r customer=property/r
}
