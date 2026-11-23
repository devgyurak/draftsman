namespace Shop.Amb
{
    public class Compare
    {
        protected static int Order = 1, b = 2, Customer = 3, d = 4;
        static bool F(bool x, bool y) => x;
        public Compare() { }
        public Compare(bool x, bool y) { }
        public bool this[bool x, bool y] => x;
        public object A() => new bool[] { Order < b, Customer > d };
        public object B() { bool[] xs = [Order < b, Customer > d]; return xs; }
        public object C() => new Compare(Order < b, Customer > d);
        public object D() => this[Order < b, Customer > d];
        public object E() { System.Func<bool, bool, bool> f = F; return f(Order < b, Customer > d); }
        public object G() => new System.Collections.Generic.List<bool> { Order < b, Customer > d };
        public object H() => F(y: Order < b, x: Customer > d);
        public object I() => F(Order < b, Customer > d) ? Status.Open : Status.Closed;
    }
    public class Derived : Compare
    {
        public Derived() : base(Order < b, Customer > d) { }
    }
}
