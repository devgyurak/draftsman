package shop

class Req
class Cfg
class Ctx
class Job
class Box<T>
annotation class Api
typealias Handler = suspend (Req) -> Unit
typealias Handler2 = suspend Ctx.(Req, Cfg) -> Job
typealias Plain = (Req) -> Cfg
