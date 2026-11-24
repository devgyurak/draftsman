package shop

interface Source<T> { fun next(): T }
open class Box<T>
// aliases of no class of their own: the key answers the class of the type they stand for
typealias Cashes = List<Money>
typealias Handler = (Money) -> Unit

// an alias as a type argument of a local class's or an anonymous object's supertype
class Aliases {
    fun f(): Any {
        val a = object : Source<Cash> { override fun next(): Cash = Cash(1) }   //> Source=shop.Source/t Cash=shop.Money/t Cash=shop.Money/t Cash=shop.Money/r
        class Local : Box<Cash>(), Source<Cash> { override fun next(): Cash = Cash(2) }   //> Box=shop.Box/t Cash=shop.Money/t Source=shop.Source/t Cash=shop.Money/t Cash=shop.Money/t Cash=shop.Money/r
        val c: Cashes = listOf()   //> Cashes=kotlin.collections.List/t listOf=function/r
        val d: Handler = { }   //> Handler=kotlin.Function1/t
        return listOf(a, Local(), c, d)   //> listOf=function/r a=var/r Local=local/r c=var/r d=var/r
    }
}
