using L2 = Lib;
using S2 = Lib.Sub;

namespace Shop.Uses
{
    // #57: a type through an alias of a namespace, `.` and `::`; the alias's target is
    // read from the global namespace (not Shop.Lib)
    public class A
    {
        public L2.Order O;
        public L2::Order P;
        public S2.Item I;
        public S2::Order Q;
        public L2.Sub.Item J;
        public void M(L2.Item x, S2::Item y) {}
    }
}

namespace Shop
{
    // an alias in a namespace block: its target from Shop outward (Shop.Lib.Sub)
    using B2 = Lib.Sub;

    public class B
    {
        public B2.Item I;
        public L.Order Nested;
    }
}
