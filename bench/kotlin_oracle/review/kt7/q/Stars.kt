package q

import shop.Order.*
import shop.Kind.*

class St {
    fun a() = Part()
    fun b() = A.name
    fun c() { val p: Part? = null; println(p) }
    fun d() = B
}
