package p;
import java.util.*;
import java.util.function.Function;
class Sink {
    void drain(Collection<? super Node> out) {}
    Map<? super Key, ? extends List<? super Other>> m;
    Conn.@Nn Response res;
    p.Conn.@Nn Req req;
    List<Conn.@Nn Response> list;
    @Nn Node[] arr;
    Node @Nn [] arr2;
    Function<? super Node, ? extends Key> fn;
    <T extends Comparable<? super Key>> T pick(T t) { return t; }
}
enum Provider { JDK, @Unstable OPENSSL, @Deprecated OLD }
enum Kind {
    @Unstable A { void f(Node n) {} },
    B;
    void f(Node n) {}
}
