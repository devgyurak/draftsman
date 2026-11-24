package q

import other.*
import shop.*
import shop.Token as Tok

class AQ {
    fun a() = Token()
    fun b() = Token.x
    fun c() { val t: Token? = null; println(t) }
    fun d() = Tok.x
    fun e(t: Token) = t
}
