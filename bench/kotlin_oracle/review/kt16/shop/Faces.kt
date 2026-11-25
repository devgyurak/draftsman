package shop

interface Face {
    class N
    fun own(x: N): N?
    class M(val n: N)
}

interface Face2 : Face {
    fun f(x: N): N?
}

abstract class Mid : Face {
    abstract val n: N
}

class Leaf(val a: N) : Mid() {
    override val n: N = N()
    override fun own(x: Face.N): Face.N? = null
    inner class In(val i: N) {
        fun g(): Any = N()
    }
}

object Single : Face {
    val n: N? = null
    override fun own(x: Face.N): Face.N? = null
}

enum class Kind(val n: N?) : Face {
    A(null);
    override fun own(x: Face.N): Face.N? = null
    fun h(): Any = N()
}
