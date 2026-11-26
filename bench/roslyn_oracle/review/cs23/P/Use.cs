using L = Lib;
using LS = Lib.Sub;
using Order = Shop.Order;

namespace App
{
    public class A
    {
        public L.Order Q;
        public L::Order R;
        public LS.Deep D;
        public L.Sub.Deep D2;
        public L.Box<LS.Deep> B;
        public Order O;
        public L.Order Get(L::Box<L.Order> b) => null;
        public object M() => new L.Order();
    }

    public class C : L.Order { }
}

namespace Shop.Inner
{
    public class B2
    {
        public L.Order Q;
        public L::Order R;
        public object M() => new L.Order();
    }
}
