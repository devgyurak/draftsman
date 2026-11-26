package shop

class Pipe(val h: Handler, val h2: Handler2) {
    fun add(x: Handler, y: Plain) {}
    var cfg: (Cfg.() -> Unit) = {}
    fun filter(block: ((Req) -> Boolean)?, other: (suspend (Job) -> Ctx)?) {}
    var flag: Int = 0
        @Api set
    val ro: Int
        @Api get() = 1
    private val Box<out Job?>.done: Boolean get() = true
    val Ctx.name: String get() = ""
    fun named(Req: Int, Cfg: String): Job? = null
    fun lam(f: (Req: Int, Cfg) -> Unit) {}
}

enum class Mode { A, @Api B, C }

class Service {
    context(c: Ctx) fun run(r: Req) {}
    context(Ctx: Cfg) fun named(): Job? = null
}
