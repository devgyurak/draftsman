package shop

class Inner2 {
    fun a(): Any = with(Inner()) { Loading2 }
}
class V3 {
    fun Inner.e(): Any = Loading2
    fun b(): Any = Loading2
}
