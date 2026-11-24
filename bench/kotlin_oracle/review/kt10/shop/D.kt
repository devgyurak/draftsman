package shop

object Registry { val size = 0 }
object Other { val size = 0 }
class Z1(val p: Any = Registry) {
    fun a(): Any = Registry
    fun b(): Int = Registry.size
}
class Z2(val p: Any = Other.size) {
    fun a(): Any = Other
    fun b(): Int = Other.size
}
class Z3(p: Any = Registry, val q: Int = 1) {
    fun a(): Any = Registry
}
class Z4 {
    fun f(x: Any = Registry): Any = Registry.size
}
