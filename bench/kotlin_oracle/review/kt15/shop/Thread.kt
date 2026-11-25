package shop

// #10: a nested type of a superclass outside the sources comes before the package's
class State

class T(val s: State) : Thread() {
    fun f(x: State): State? = null
    val p: State? = null
    fun g(): Any? = State.NEW
}

// the package's State where no superclass has one
class Plain(val s: State) {
    fun f(x: State): State? = null
}
