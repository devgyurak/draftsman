package shop

class Money(val amount: Int) { companion object { val ZERO = Money(0); fun of(x: Int) = Money(x) } }
class Order { companion object { fun create() = Order() } }
object Registry { val size = 0 }
class Ctx { fun Money(x: Int) = x; val Order = 1; val Registry = 2; class Part }
class name { companion object { val x = 1 } }
typealias T2 = Thread
typealias LC = List<Ctx>
interface Face { fun id(): Int = 1 }
