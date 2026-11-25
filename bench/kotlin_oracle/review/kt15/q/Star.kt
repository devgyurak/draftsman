package q

import p.*

// #8: a star import of a package of the sources comes before the default imports
// (kotlin.Result, kotlin.Pair); the file's own package comes before the star import
class U8(val r: Result, val o: Pair) {
    fun f(x: Result): Result? = null
    val g: Pair? = null
    fun h(): Any = Result()
}
