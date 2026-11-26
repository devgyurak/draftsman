package shop

import other.Widget

class Widget(val s: String)

class S {
    fun d(w: Widget) = w
    val f: Widget? = null
    fun g(): Int = Widget(1)
}
