package q

import p.*

class Derived2 : Iface {
    fun viaInterface() = Nested()
}
fun Base.ext2() = Inner()
