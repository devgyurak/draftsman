using N = global::Lib;

namespace Shop.Inner
{
    using M = global::Lib.Sub;

    public class A
    {
        public M::Deep F1;
        public M.Deep F2;
        public N::Order F3;
        public N.Order F4;
        public N::Sub.Deep F5;
        public N::Box<M::Deep> F6;
        public M::Deep Get(N::Order o) => null;
        public object B1() => new M::Deep();
        public object B2() => M::Deep.Count;
        public object B3() => new M.Deep();
        public object B4() => new N::Order();
        public object B5() => N::Order.Make();
        public object B6() => typeof(N::Sub.Deep);
    }
    public class C : N::Order { }
    public class D : N::Box<M::Deep> { }
}
