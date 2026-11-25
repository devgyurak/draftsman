package a

class NodeList : ArrayList<Node>()
class Gen<T> : ArrayList<T>()
class Nested : HashMap<String, List<Item>>(), Comparable<Nested> {
    override fun compareTo(other: Nested): Int = 0
}
class UsesB : ArrayList<b.Node>()
class Sub : Base<Item>()
class Deleg(private val d: List<Item>) : List<Item> by d

typealias Vector = List<Item>
typealias Provider = Node

class Holder(val items: Vector, val p: Provider)
