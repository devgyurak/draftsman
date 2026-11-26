package shop

import other.Widget
import other.Gadget

// #36: an alias of a suspend function type; a parameter named like a class names none
typealias Handler = suspend (Logger: Req) -> Unit

class Pipe(val h: Handler) {
    fun add(x: Handler) {}
    // #40: function types in parentheses
    var cfg: (Cfg.() -> Unit) = {}
    fun filter(block: ((Req) -> Boolean)) {}
    // #39: context parameters, one named like a class
    context(c: Ctx)
    fun run() {}
    context(Logger: Job)
    fun log() {}
    // #41: an annotation on an accessor
    var flag: Int = 0
        @Api set
    // #42: an extension property's receiver
    private val Box<out Job?>.done: Boolean get() = true
    // #55: `import other.Widget` brings in a function: the type is the package's
    fun d(w: Widget, g: Gadget) = w
    fun c(c: cs.Charset) {}
}

// #41: annotations on enum entries
enum class Mode { A, @Api B, @Tag(Req::class) C }
