package shop

open class Order(val id: Int) {
    class Line
    inner class Part
    companion object { fun create() = Order(1); class Ser; val Empty = Order(0) }
    open fun describe(): String = "o"
}
class Money(val v: Int) {
    companion object Named { operator fun invoke(s: String) = Money(s.length); val Zero = Money(0) }
}
class Customer(val name: String)
class Box<T>(val item: T)
object Registry { val all = listOf<Order>(); operator fun invoke(n: Int) = n }
enum class Status { New, Paid }
fun interface Action { fun run() }
interface Holder { class Nested; fun hold(): String = "h" }
class Ticket { companion object Factory : Action { override fun run() { Money(1) } } }
annotation class Anno(val k: kotlin.reflect.KClass<*>)

typealias Cash = Money
typealias Cash2 = Cash
typealias Handler = (Money) -> Unit
typealias Cashes = List<Money>
typealias Gen<T> = Box<T>
typealias Err = IllegalStateException
typealias Line2 = Order.Line
