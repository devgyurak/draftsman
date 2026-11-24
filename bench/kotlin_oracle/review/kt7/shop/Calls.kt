package shop

fun Order.Gadget(): Int = 1

class U {
    fun a() = Widget("s")
    fun b(o: Order) = with(o) { Gadget() }
    fun c() = Gadget.x
    fun d() {
        fun Money(s: String) = 1
        println(Money("s"))
    }
    fun e(Money: (Int) -> Int) = Money(1)
    val Tool: () -> Int = { 1 }
    fun f() = Tool()
    fun g() = shop.Tool()
    fun Helper(s: String) = 1
    fun h() = Helper("s")
    fun i() = Helper(3)
    fun j() = Helper.x
    fun k(): Any = ::Flag
    fun l(): Any = Flag::class
}
