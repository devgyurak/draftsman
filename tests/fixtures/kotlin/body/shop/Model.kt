package shop

open class Order(val id: Int) {
    class Line
    object Tools { fun go() = 1 }
    companion object {
        fun create() = Order(1)   //> Order=shop.Order/r
        val Empty = Order(0)   //> Order=shop.Order/r
    }
    fun Member(): Int = 1
}

class Customer(val name: String)

// a class and a function of one name: the arguments pick
class Money(val v: Int) {
    companion object { operator fun invoke(s: String) = Money(s.length) }   //> Money=shop.Money/r s=- s=var/r
}
fun Money(a: Int, b: Int): Money = Money(a + b)   //> Money=- Money=- Money=shop.Money/r a=- b=- a=var/r b=var/r

object Registry { val all = listOf<Order>() }   //> listOf=function/r Order=shop.Order/t

enum class Status(val code: Int) { New(1), Paid(2) }

typealias Cash = Money

fun interface Action { fun run() }

class Problem : Exception()

@Target(AnnotationTarget.TYPE) annotation class Mark

interface Holder { class Nested }

// a companion object with a supertype is a type of its own in ir.json
class Ticket { companion object Factory : Action { override fun run() {} } }

// a type named in lower case
class engines

// a capitalized top-level property and function: values, not types
val Plugin = Order(3)   //> Order=shop.Order/r
fun Widget(): Customer = Customer("w")   //> Customer=- Customer=shop.Customer/r

class Result
