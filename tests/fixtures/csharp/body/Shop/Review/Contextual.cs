using System.Collections.Generic;
using Shop.Rev.Odd;

namespace Shop.Rev.Odd
{
    // a type named as one of C#'s contextual keywords
    public class var { public static int Count; }
}

namespace Shop.Rev.Ctx
{
    public class Names
    {
        // with a type named var in scope, `var` names it
        public object A() => var.Count;   //> var=Shop.Rev.Odd.var/r
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
}
