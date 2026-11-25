package shop

// #11: an interface passes on no nested type
interface Face {
    class N
}

class N

class Impl(val a: N) : Face {
    fun f(x: N): N? = null
    val p: N? = null
    fun g(): Any = N()
}

// a superclass's does pass on
open class Abs {
    class M
}

class M

class Sub2(val a: M) : Abs() {
    fun f(x: M): M? = null
    fun g(): Any = M()
}
