package shop

class Sub : Base() {
    fun a() = Tool()
    fun b() = Helper()
    fun c() = Flag.toString()
    fun d() = Prop.toString()
    fun e() = Nested()
    fun f() = InComp()
    fun g() = Nested.y
    fun h() { val x: Nested? = null; val y: InComp? = null; println("$x $y") }
    fun i() = listOf(Tool.x, Helper.x)
    fun j() = InComp.x
}
class Impl : Face {
    fun a() = N.x
    fun b() { val v: N? = null; println(v) }
    fun c() = N()
}
class Deep {
    inner class In : Base() {
        fun a() = Tool()
        fun b() { val x: Nested? = null; println(x) }
    }
    fun viaObject() = object : Base() {
        fun a() = Helper()
        fun b() = Nested()
        fun c() = Flag.toString()
    }
    fun viaLocal() {
        class L : Base() { fun a() = Prop.toString(); fun b() = Tool.x }
        println(L().a())
    }
    fun plain() = Nested.x
}
