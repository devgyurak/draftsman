package shop

open class B { fun Plain(): Int = 1 }
class C : B() {
    fun a(): Any = Plain()
    fun Inner(): Int = 2
    fun b(): Any = Inner()
}
class D {
    class Inner
    companion object { fun Inner(x: Int) = x }
    fun a(): Any = D.Inner(1)
    fun b(): Any = D.Inner()
}
