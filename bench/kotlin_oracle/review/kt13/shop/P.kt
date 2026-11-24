package shop

object Caches { val x = 1 }
object FieldHolder { val x = 1 }
object eetop { val x = 1 }
object holder { val x = 1 }
object Itr { val x = 1 }
object elementData { val x = 1 }
object modCount { val x = 1 }
object MAX_PRIORITY { val x = 1 }

class W : Thread() {
    fun a(): Any = Caches
    fun b(): Any = Caches.x
    fun c(): Any = eetop
    fun d(): Any = holder.x
    fun e(): Any = FieldHolder
    fun f(): Any? { val v: Caches? = null; return v }
    fun g(): Any = MAX_PRIORITY
}
class L : java.util.ArrayList<Int>() {
    fun a(): Any = Itr
    fun b(): Any = Itr.x
    fun c(): Any = elementData
    fun d(): Any = modCount
    fun e(): Any? { val v: Itr? = null; return v }
}
