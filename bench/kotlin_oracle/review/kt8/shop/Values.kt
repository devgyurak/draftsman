package shop

enum class Phase { Loading, Done;
    fun a(): Any = Loading
}
class V(val Ready: Int) {
    fun a(x: Any): Any = when (x) { Loading -> 1; Ready -> 2; else -> 3 }
    fun b(): Any { val Loading = 5; return listOf(Loading, Order) }
    fun c(): Any = listOf(Loading, Order, Phase.Done)
    fun d(): Any = "$Loading ${Ready}"
    fun e(): Any = Order.create()
}
class W { val x: Any = Ready; val y = Loading }
