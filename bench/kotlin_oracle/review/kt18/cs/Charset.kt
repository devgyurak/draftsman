package cs

// #37: an expect class (here a plain declaration of the id) and an actual typealias of an
// outside class: the compiler's answer is the class; the key reads an actual typealias so
expect abstract class Charset
actual typealias Charset = java.nio.charset.Charset
