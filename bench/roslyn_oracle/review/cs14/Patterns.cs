namespace Shop.Pat
{
    public class VarPatterns
    {
        public object A(object o) => o is var Order ? Order.GetHashCode() : 0;
        public object B(Holder h) => h is { Order: var Money } ? Money.Count : 0;
        public object C(Holder h) { switch (h) { case var Order: return Order.Money.Count; } }
        public object D(Holder h) => h switch { var Order => Order.Money.Count };
        public object E(Holder h) => h switch { { Order: { } Money } => Money.Count, _ => 0 };
        public object F(Holder[] hs) => hs is [var Order, ..] ? Order.Money.Count : 0;
        public object G(Holder[] hs) => hs is [.. var Money] ? Money.Length : 0;
        public object H((Holder, int) t) => t is (var Order, var n) ? Order.Money.Count : 0;
        public object I(Holder h) => h is Holder { } Order ? Order.Money.Count : 0;
        public object J(Holder h) => h is not null and var Money ? Money.Order.Count : 0;
        public object K() => Status.Count;
    }
}
