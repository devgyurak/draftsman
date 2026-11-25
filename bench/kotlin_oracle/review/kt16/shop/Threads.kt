package shop

open class MyThread : Thread()

class T2(val s: State) : MyThread() {
    val h: UncaughtExceptionHandler? = null
    fun f(x: State): State? = null
    fun g(): Any = State.NEW
}

abstract class MyMap : Map<String, Int> {
    abstract val first: Entry<String, Int>
}

abstract class JMap : java.util.AbstractMap<String, Int>() {
    abstract val e: SimpleEntry<String, Int>
    abstract val x: Entry<String, Int>
}

class Plain(val s: State) {
    fun f(): Any = State()
}
