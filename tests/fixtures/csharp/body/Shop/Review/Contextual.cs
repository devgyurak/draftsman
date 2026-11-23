using System.Collections.Generic;

namespace Shop.Rev.Ctx
{
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
