using L = Lib;

namespace Shop.Inner
{
    using M = global::Lib.Sub;

    [L::Mark(typeof(L::Order))]
    public class A<T> where T : L::Order
    {
        public object B1() => new L::Order[3];
        public object B2() => default(L::Order);
        public object B3(object o) => o as L::Order;
        public object B4(object o) => o is L::Order x ? x : null;
        public object B5() => nameof(G);
        public object B6() => L::Box<int>.Make();
        public object B7() => L::Util.Id<G::Order>(null);
        public object B8() { L::Order x = null; return x; }
        public object B9() { System.Func<L::Order, M::Deep> f = (L::Order o) => null; return f; }
        public object B10() => L::Order.Line.Make();
        public object B11() => L::Order.Max;
        public object B12() => L::Kind.A;
        public object B13() => M::Deep.Count;
        public object B14() => global::Lib.Order.Make();
        public object B15() => global::Lib.Kind.B;
        public object B16(object o) => o switch { L::Order => 1, M::Deep d => 2, _ => 0 };
        public object B17() => new L::Rec(1) with { N = 2 };
        public object B18() { foreach (L::Order o in new L::Order[0]) { } return null; }
        public object B19() => typeof(L::Box<>);
        public object B20() => new System.Collections.Generic.List<L::Order>();
        public object B21() { var L = 1; return new L::Order(L); }
        public object B22() => Lib.Order.Make();
    }
    public class C1(int n) : L::Order(n), L::IThing { }
    public record R2(int N) : L::Rec(N);
    public struct S1 : L::IThing { }
    public interface I1 : L::IThing { }
    public class D1 : global::Lib.Order { }
    public class D2 : Lib.Order { }
}
