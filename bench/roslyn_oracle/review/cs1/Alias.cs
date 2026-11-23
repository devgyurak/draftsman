using Shop;
using Order = Lib2.Order;
using O = Lib.Order;
using L = Lib;

namespace Other.Al
{
    // an alias comes before a using's types at the same level
    public class Uses
    {
        public object M() => new Order();
        public object N() => Order.Count;
        public object P() => new L::Order();
        public object Q() => L::Order.Count;
        public object R() => new L.Order();
        public object S() => L.Order.Count;
    }
}
namespace Shop.Sub
{
    // the alias's target is bound where it is declared: Lib.Order, not Shop.Lib.Order
    public class Target
    {
        public object M() => new O();
        public object N() => O.Count;
    }
    public class Nested
    {
        public class O { public static int Count = 0; }
        public object M() => new O();
        public object N() => O.Count;
    }
}
