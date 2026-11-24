package shop

class Box<Money> {
    fun f(x: Any) { val y = x as Money; val z: List<Money> = listOf(y); println(z) }
    fun g() = Order()
    fun <Order> h(x: Any): Any? { val y: Order? = null; return y ?: x }
    fun i() { val o: Order? = null; println(o) }
    class In { fun j() { val m: Money? = null; println(m) } }
    inner class In2 { fun k(x: Any) { val m = x as Money; println(m) } }
}
