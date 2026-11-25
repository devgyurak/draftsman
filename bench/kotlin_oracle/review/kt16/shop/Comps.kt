package shop

open class Root {
    class Deep
    companion object {
        class InComp
    }
}

open class Base : Root() {
    class Reg
    val d: Deep? = null
    val c: InComp? = null
}

class Sub(val a: InComp, val r: Reg, val d2: Deep) : Base() {
    fun f(x: Reg): Deep? = null
    class Nested(val i: InComp, val r: Reg)
    fun g(): Any = listOf(InComp(), Reg(), Deep())
    companion object {
        val x: Reg? = null
    }
}

class Own {
    companion object {
        class InComp
    }
    val a: InComp? = null
    class In2(val i: InComp)
}
