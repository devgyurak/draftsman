namespace Shop.Pat
{
    public class Outer
    {
        public static Holder Order = new Holder();
        public class In
        {
            public object A() => Order.Money.Count;
            public object B() => Status.Count;
        }
        public struct InS { public object A() => Order.Money.Count; }
    }
    public class OuterBase { protected static Holder Status = new Holder(); }
    public class Outer2 : OuterBase
    {
        public class In { public object A() => Status.Order.Count; }
    }
    public class TParams
    {
        public object A<Order>() => typeof(Order);
        public object B() { T Local<T, Money>(T x) => x; return typeof(Money); }
        public object C<Status>(Status s) where Status : Holder => s.Order.Count;
        public object L() { goto Order; Order: return Money.Count; }
    }
}
