package q

import p.*
import p.Money as Coin
import r.Money

// #9: nor through `import p.*`; `Money` is the one imported by name
class Holder(val a: Money, val b: Coin, val c: Other) {
    fun f(x: Money): Coin? = null
}
