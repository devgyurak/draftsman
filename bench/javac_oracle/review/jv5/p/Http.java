package p;
import java.util.Collection;
import java.util.function.Consumer;
// #27: a type annotation inside a qualified name, beside a top-level Response;
// #26: `? super X`, beside a type parameter named like the class T
public class Http {
    private Conn.@Nullable Response res;
    public Conn.@Nullable KeyVal data(String key) { return null; }
    void drain(Collection<? super Item> out) {}
    <T> void each(Consumer<? super T> c) {}
    void walk(Consumer<? super Conn.@Nullable Response> c) {}
}
