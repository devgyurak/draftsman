using Shop.Odd;

namespace Shop.Ctx
{
    public class Names
    {
        public object A() { var x = new var(); return x; }
        public object B() => var.Count;
        public object C() { dynamic d = new dynamic(); return d; }
        public object D() => dynamic.Count;
        public object E() => nameof.Count;
        public object F() => value.Count;
        public int P { get => field.GetHashCode(); set { int v = value.GetHashCode(); } }
        public object Q() => field.Count;
        public object G() { int await = Order.Count; return await; }
        public object H(object Order) => nameof(Order);
    }
}
