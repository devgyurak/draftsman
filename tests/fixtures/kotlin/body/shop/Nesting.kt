package shop

// a type sees the nested types of its superclasses by simple name, but not those of an
// interface, nor those of a superclass's companion object: its own ones it sees
interface Face { class N; fun id(): Any = N() }   //> N=- N=shop.Face.N/r
open class Base {
    companion object { class InComp; fun make(): Any = InComp() }   //> InComp=- InComp=shop.Base.InComp/r
    fun own(): Any = InComp()   //> InComp=shop.Base.InComp/r
    class Inner { fun f(): Any = InComp() }   //> InComp=shop.Base.InComp/r
}
class N
class InComp
class Sub : Base() {
    fun a(): Any = InComp()   //> InComp=shop.InComp/r
    fun b(): Any? { val x: InComp? = null; return x }   //> InComp=shop.InComp/t x=- x=var/r
}
class Impl : Face {
    fun a(): Any = N()   //> N=shop.N/r
    fun b(): Any? { val x: N? = null; return x }   //> N=shop.N/t x=- x=var/r
}
