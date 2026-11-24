package shop

class Money(val v: Int)
open class Box<T>
interface Source<T> { fun next(): T }
typealias Cash = Money
typealias CashBox = Box<Cash>

class AliasArgs {
    fun f(x: Any): Any {
        val a = object : Source<Cash> { override fun next(): Cash = Cash(1) }
        val b: List<Cash> = listOf<Cash>()
        val c = x is Source<Cash>
        val d = object : Box<Cash>() { }
        class Local : Box<Cash>(), Source<Cash> { override fun next(): Cash = Cash(2) }
        val e: (Cash) -> Cash = { it }
        val g = Box<Cash>()
        val h: CashBox? = null
        val i = x as? Map<String, Cash>
        fun loc(p: List<Cash>): Source<Cash>? = null
        val j = { p: Box<Cash> -> p }
        return listOf(a, b, c, d, e, g, h, i, j)
    }
    val prop = object : Source<Cash> { override fun next(): Cash = Cash(3) }
}
