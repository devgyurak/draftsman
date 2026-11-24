package q

import shop.Kind.A

class IV {
    fun a(): Any = A
    fun b(): Any = A.name
    fun c(): Any? { val v: A? = null; return v }
    fun d(): Any = listOf(A)
}
