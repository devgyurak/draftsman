package shop

import other.*
import shop.Token as Tok

class AH {
    fun a() = Token()
    fun b() = Token.x
    fun c() { val t: Token? = null; println(t) }
    fun d() = Tok()
    fun e(t: Token) = t
}
class Impl2 : Face2 {
    fun a() = Helper2()
    fun b() = Flag2.x
}
