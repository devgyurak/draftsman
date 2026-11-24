package shop

// forms the review rounds found (bench/kotlin_oracle/review/kt9 - kt13)
object Proxy : Action { override fun run() {} }

// an accessor on the line after its property, a class's delegate, a default value
class Accessors(val p: Any = Registry) : Action by Proxy {   //> Registry=shop.Registry/r Proxy=shop.Proxy/r
    val a: Any
        get() = Registry.all   //> Registry=shop.Registry/r
    var b: Any
        get() = Customer("g")   //> Customer=shop.Customer/r
        set(v) { Customer(v.toString()) }   //> v=- Customer=shop.Customer/r v=var/r
    fun f(): Any = Registry   //> Registry=shop.Registry/r
}

// an extension's receiver: a type parameter's bounds, an alias, outside supertypes
class Ctx { fun Customer(x: Int) = x; val Registry = 1 }   //> x=- x=var/r
typealias CtxAlias = Ctx
open class Worker : Thread()
object name
object MAX_PRIORITY
class Receivers2<U : Ctx> {
    fun <T : Ctx> T.a(): Any = Customer(1)   //> Customer=function/r
    fun <T> T.b(): Any where T : Ctx = Registry   //> Registry=property/r
    fun CtxAlias.c(): Any = Customer(2)   //> Customer=function/r
    fun Worker.d(): Any = name   //> name=property/r
    fun <T : Thread> T.e(): Any = name   //> name=property/r
    fun U.f(): Any = Customer(3)   //> Customer=function/r
    fun <T> T.g(): Any = Customer("x")   //> Customer=shop.Customer/r
    fun Thread.h(): Any = MAX_PRIORITY   //> MAX_PRIORITY=shop.MAX_PRIORITY/r
}

// a library supertype's private names hide nothing
object eetop
object Caches
class Worker2 : Thread() {
    fun a(): Any = eetop   //> eetop=shop.eetop/r
    fun b(): Any = Caches   //> Caches=shop.Caches/r
    fun c(): Any = MAX_PRIORITY   //> MAX_PRIORITY=property/r
}

// receivers: an alias of a library type, an anonymous function's, an annotated one (kt14)
typealias ThreadAlias = Thread
class Receivers3 {
    fun ThreadAlias.a(): Any = name   //> name=property/r
    val b = fun Ctx.() = Customer(1)   //> Ctx=shop.Ctx/t Customer=function/r
    fun c(): Any = fun Ctx.() = Registry   //> Ctx=shop.Ctx/t Registry=property/r
    fun @receiver:Suppress("x") Ctx.d(): Any = Customer(2)   //> Customer=function/r
}
