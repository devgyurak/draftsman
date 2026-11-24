package shop

interface Face { fun id(): Int = 1 }
object Proxy : Face
object Registry { val size = 0 }
open class Taker(val x: Any)
class D1 : Face by Proxy
class D2 : Taker(Registry), Face by Proxy {
    fun a(): Any = Proxy
}
object D3 : Taker(Registry), Face by Proxy
class D4(val f: Face = Proxy) : Face by f
