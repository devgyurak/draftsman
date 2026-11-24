package p

open class Base(val n: Int) {
    class Inner
    object Tools { fun go() = 1 }
    companion object { fun make() = Base(1); val Zero = Base(0) }
    fun Member(): Int = 1
    val Prop: Int = 2
}
interface Iface { class Nested; fun IfaceFun(): Int = 1 }
class Money(val v: Int) { companion object { operator fun invoke(s: String) = Money(s.length) } }
fun Money(a: Int, b: Int): Money = Money(a + b)
class Widget
fun Widget(x: Int): Widget = Widget()
object Registry { val all = listOf<Base>() }
enum class Color(val m: Money) { Red(Money(1)), Green(Money(2)); companion object { val Default = Red } }
typealias Cash = Money
fun interface Action { fun run() }
val Plugin = Base(3)
class Result
class Member
class Dup
class MyErr : Exception()
sealed interface State { data object Loading : State; data class Done(val m: Money) : State }
annotation class Mark
class Dsl { fun Widget(): Int = 0; val Registry = 1 }
fun dsl(b: Dsl.() -> Unit) {}
