using System;
using System.Collections.Generic;
using Vector = System.Collections.Generic.List<A.Item>;
using Provider = A.Node;

namespace A
{
    public class NodeList : List<Node> {}
    public class Gen<T> : List<T> {}
    public class Nested : Dictionary<string, List<Item>>, IComparable<Nested>
    {
        public int CompareTo(Nested? o) => 0;
    }
    public class UsesB : List<B.Node> {}
    public class Sub : Base<Item> {}
    public class Q : Outer<Item>.Inner<Node> {}
    public class Holder
    {
        public Vector Items = new();
        public Provider? P;
    }
}
