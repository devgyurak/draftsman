package p;
import java.util.List;
import java.util.Map;
import q.Item;

class A extends Base<Item, Map<String, q.Other>> implements Face<q.Deep>, Comparable<A> {
    public int compareTo(A o) { return 0; }
}
class G<Key> extends Base<Key, p.Key> {}
class W extends Base<List<? extends Item>, Key[]> {}
class N extends Base<@Nn Item, Key> {}
class In extends Base<Base.Inner, Base<Key, Item>> {}
interface I2 extends Face<Item>, java.util.function.Supplier<Key> {}
enum E implements Face<Key> { X }
record Rec(int n) implements Face<Item> {}
class Self<T extends Self<T>> extends Base<T, Self<T>> {}
