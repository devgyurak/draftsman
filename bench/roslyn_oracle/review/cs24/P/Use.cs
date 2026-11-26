using L = Lib;

namespace Shop.Inner
{
    using M = Lib.Sub;

    [L::Mark]
    public class A
    {
        public L::Order F1;
        public L::Sub.Deep F2;
        public L::Box<L::Order> F3;
        public L::Box F4;
        public L::Order.Line F5;
        public G::Order F6;
        public M::Deep F7;
        public L.Order F8;
        public G.Order F9;
        public M.Deep F10;
        public global::Lib.Box<L::Sub.Deep> F11;
        public L::Order[] F12;
        public System.Collections.Generic.List<L::Order> F13;
        public L::Order Get(G::Box<M::Deep> b, L::Box<int> c) => null;
        public object B1() => new L::Order();
        public object B2() => L::Order.Make();
        public object B3() => typeof(L::Sub.Deep);
        public void B4() { L::Util.Run(); }
        public object B5(object o) => (G::Order)o;
        public object B6(object o) => o is M::Deep ? 1 : 0;
        public object B7() => new L::Box<G::Order>();
    }
    public class C : L::Order { }
    public class D : L::Box<M::Deep> { }
}

namespace Shop.Other
{
    using LS = L::Sub;

    public class E
    {
        public LS::Deep F1;
        public LS.Deep F2;
        public object B1() => new LS::Deep();
    }
}
