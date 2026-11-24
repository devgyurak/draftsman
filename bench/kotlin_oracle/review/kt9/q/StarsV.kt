package q

import shop.Kind.*

class SV {
    fun a(): Any = B
    fun b(): Any? { val v: B? = null; return v }
    fun c(): Any = B.x
    fun d(): Any = A
}
