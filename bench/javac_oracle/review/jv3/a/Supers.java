package a;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;

class NodeList extends ArrayList<Node> {}

class Gen<T> extends ArrayList<T> {}

class Nested extends HashMap<String, List<Item>> implements Comparable<Nested> {
    public int compareTo(Nested o) { return 0; }
}

class UsesB extends ArrayList<b.Node> {}

class Sub extends Base<Item> implements Comparable<Sub> {
    public int compareTo(Sub o) { return 0; }
}

class SubIn extends Base.In<Node> {}

class Multi
        extends HashMap<
                Item,
                Node> {}

class Holder {
    Provider<Item> provider;
}

class GenSub<T> extends Base<List<T>> {}
