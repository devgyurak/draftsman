package shop

class Money(val amount: Int) {
    companion object { val ZERO = Money(0); fun of(x: Int) = Money(x) }
}
class Order {
    class Part
    inner class Line
    companion object { fun create() = Order() }
}
object Registry { fun find(): Money = Money.ZERO; val size = 0 }
enum class Kind { A, B }
interface Face { class N; fun id(): Int = 1 }
open class Base {
    class Nested { companion object { val y = 1 } }
    companion object { class InComp { companion object { val y = 1 } }; fun Helper(): Int = 1; val Flag = 1 }
    fun Tool(): Int = 2
    val Prop = 3
}
class Tool { companion object { val x = 1 } }
class Helper(val n: Int = 0) { companion object { val x = 1 } }
class Flag { companion object { val x = 1 } }
class Prop { companion object { val x = 1 } }
class N { companion object { val x = 1 } }
class Nested { companion object { val x = 1 } }
class InComp { companion object { val x = 1 } }
class Widget(val s: String)
class Gadget { companion object { val x = 1 } }
class Ctx { fun Money(x: Int) = x; val Order = 1; class Part }
class Token { companion object { val x = 1 } }
interface Face2 { companion object { fun Helper2(): Int = 1; val Flag2 = 1 } }
class Helper2 { companion object { val x = 1 } }
class Flag2 { companion object { val x = 1 } }
