using System.Collections.Generic;
using Shop.Rev.Odd;

namespace Shop.Rev.Odd
{
    // types named as C#'s contextual keywords
    public class var { public static int Count; }
    public class value { public static int Count; }
    public class field { public static int Count; }
}

namespace Shop.Rev.Ctx
{
    public class Names
    {
        // with a type named var in scope, `var` names it
        public object A() => var.Count;   //> var=Shop.Rev.Odd.var/r
        // `value` in a setter is its parameter, `field` in a property's accessor its backing field
        public int P { get => field.GetHashCode(); set { int v = value.GetHashCode(); } }
        public object B() => value.Count;   //> value=Shop.Rev.Odd.value/r
    }

    // `F(Order < b, Customer > d)` is two comparisons, not a declaration; after `out` it is one
    public class Comparisons
    {
        static bool F(bool a, bool b) => a;
        static void G(out List<Order> x) => x = new List<Order>();   //> List=- Order=- List=System.Collections.Generic.List/t Order=Shop.Order/t
        public bool A(int Order, int b, int Customer, int d) => F(Order < b, Customer > d);   //> Order=- Customer=- Order=- Customer=-
        public void B() => G(out List<Order> x);   //> List=System.Collections.Generic.List/t Order=Shop.Order/t
        public void C() => G(x: out List<Order> y);   //> List=System.Collections.Generic.List/t Order=Shop.Order/t
    }

    // the same comparisons in a collection expression and an indexer's arguments; a
    // deconstruction's tuple (also a foreach's) declares
    public class Elements
    {
        public int Order, b, Customer, d;   //> Order=- Customer=-
        public bool this[bool x, bool y] => x;
        public bool[] A() => [Order < b, Customer > d];   //> Order=- Customer=-
        public bool B() => this[Order < b, Customer > d];   //> Order=- Customer=-
        public void C(List<(Shop.Order, int)> pairs) { foreach ((Shop.Order o, int n) in pairs) { } }   //> List=- Shop=- Order=- Shop=- Order=Shop.Order/t
    }

    // a record's base arguments are a body, as a class's are
    public record RecBase(int N);
    public record RecSub(int M) : RecBase((int)Status.Open);   //> RecBase=- Status=Shop.Status/r
}
