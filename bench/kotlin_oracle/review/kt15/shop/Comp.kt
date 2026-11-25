package shop

// #12: a type nested in a superclass's companion is not seen by a subclass
open class Base {
    companion object {
        class InComp
    }
    // Base itself and its nested types see it
    val own: InComp? = null
    class Inner(val i: InComp)
}

class InComp

class Sub(val a: InComp) : Base() {
    fun f(x: InComp): InComp? = null
    val p: InComp? = null
    fun g(): Any = InComp()
}
