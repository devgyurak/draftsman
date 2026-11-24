package shop

import kotlinx.coroutines.CoroutineScope
import kotlin.coroutines.CoroutineContext

// a library supertype the table knows: its nested types, members and statics hide
class T : Thread() {
    fun a(): Any = State.NEW
    fun b(): Any? { val s: State? = null; return s }
    fun c(): Any = MAX_PRIORITY.toString()
    fun d(): Any = Plain()
}
class S : CoroutineScope {
    override val coroutineContext: CoroutineContext get() = TODO()
    fun a(): Any = coroutineContext.toString()
    fun b(): Any? { val s: State? = null; return s }
    fun c(): Any = Plain()
}
class E : Exception() {
    fun a(): Any = Message.x
    fun b(): Any = Plain()
}
// an extension of a library type: its members are names, its nested types not
class X {
    fun Thread.a(): Any = State.NEW
    fun Thread.b(): Any = MAX_PRIORITY.toString()
    fun CoroutineScope.c(): Any = coroutineContext.toString()
    fun Thread.d(): Any = Plain()
}
