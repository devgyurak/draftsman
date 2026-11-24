package shop

class Aliases2 {
    fun f(): Any {
        val k = Cash("s")
        val l = Cash::class
        val m = Cash.Zero
        val n: Cash = Cash(1)
        return listOf(k, l, m, n)
    }
}
