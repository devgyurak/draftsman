package shop

import other.Widget
import shop.Order as Ord

class S {
    fun a() = Widget(1)
    fun b() = Widget("s")
    fun c() { val w: Widget? = null; println(w) }
    fun d(w: Widget) = w
    fun e() = Ord()
    fun g() = Ord.create()
}
