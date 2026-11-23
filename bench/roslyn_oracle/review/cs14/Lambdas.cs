using System.Collections.Generic;
using System.Linq;
namespace Shop.Pat
{
    public class Lambdas
    {
        public object A(List<Holder> hs) => hs.ConvertAll((Order) => Order.Money.Count);
        public object B(Dictionary<int, Holder> d) { foreach (var (n, Order) in d) return Order.Money.Count; return 0; }
        public object C() { System.Func<Holder, int, int> f = (Order, n) => Order.Money.Count; return f; }
        public object D() { System.Func<Holder, int> f = delegate(Holder Order) { return Order.Money.Count; }; return f; }
        public object E() { int Local(Holder Order) => Order.Money.Count; return Local(new Holder()); }
        public object F(List<Holder> hs) => from Order in hs let Money = Order.Money select Money.Count;
        public object G(List<Holder> hs) => from h in hs group h by h.Order.Count into Order select Order.Key;
        public object H(List<Holder> hs) => from h in hs join Money in hs on h.Order.Count equals Money.Order.Count into Order select Order.GetHashCode();
        public object I(List<Holder> hs) => from Holder Order in hs select Order.Money.Count;
        public object J() => Status.Count;
    }
}
