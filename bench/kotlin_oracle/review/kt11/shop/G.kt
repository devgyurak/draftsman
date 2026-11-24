package shop

class Money(val amount: Int) { companion object { val ZERO = Money(0); fun of(x: Int) = Money(x) } }
object Registry { val size = 0 }
class Err(m: String) : Exception(m)
interface Port { val a: Any; var b: Int }
class G1 {
    val a: Any get() = Money.ZERO
    val b: Any
        get() = Money.of(1)
    var c: Int
        get() = Registry.size
        set(v) = throw Err("no")
    val d: Any
        get() {
            return Money(3)
        }
    private var cached: Money? = null
    val e: Money
        get() = cached ?: Money(1).also { cached = it }
}
class G2 : Port {
    override val a: Any
        get() = Registry
    override var b: Int
        get() = Money.ZERO.amount
        set(_) = throw Err("x")
}
