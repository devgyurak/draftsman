package shop

import shop.Phase.Loading
import shop.Config.Ready

object Config { val Ready = 1 }
open class Base2 { val Plain = 1 }
interface Iface2 { val Order: Int get() = 1 }
val Inner.Loading2: Int get() = 1
object Loading2

class V2 : Base2(), Iface2 {
    fun a(): Any = Loading
    fun b(): Any = Ready
    fun c(): Any = Plain
    fun d(): Any = Order
    fun g(Loading: Int): Int = Loading
    fun h(): Any = g(Loading = 2)
    fun i(): Any = listOf(1).map { Ready -> Ready }
    fun j(): Any { val (Plain, y) = Pair(1, 2); return Plain + y }
}
class Q2 {
    object Loading
    fun a(): Any = Loading
}
