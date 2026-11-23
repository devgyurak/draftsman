using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
namespace Shop.Amb
{
    public class Forms
    {
        public object A() { System.Func<Order, Task<Order>> f = async (Order o) => o; return f; }
        public object B() { var f = Order (int x) => new Order(); return f; }
        public object C() { static Order Make() => new Order(); return Make(); }
        public async Task<object> D(IAsyncEnumerable<Order> xs) { await foreach (Order o in xs) return o; return 0; }
        public object E(List<object> xs) => from Order o in xs select o.Total;
        public object F(List<object> xs, List<Customer> cs) => from o in xs.OfType<Order>() join Customer c in cs on o.Total equals 1 select c;
        public object G(object o) => o switch { Order => 1, Customer c => 2, _ => 0 };
        public object H(object o) => o is Order or Customer;
        public object I(object o) => o is not Order;
        public object J(object o) => o is Order and { Total: > 0 };
        public object K(object o) => o is (Order or Customer) and not null;
        public object L(object o) { switch (o) { case Order: return 1; case Customer c when c != null: return 2; default: return 0; } }
        public object M(int n) => n is < Order.Max and > Customer.Min;
        public object N(object[] xs) => xs is [Order o, ..] ? o.Total : 0;
        public object P(object o) => o as Order ?? new Order();
        public object Q(object o) => o is Order x ? x.Total : Customer.Count;
        public object R(bool a, object b) => a ? (Order)b : null;
        public object S() => typeof(Order).Name + default(Status).ToString() + nameof(Customer);
        public object T() { ref readonly int r = ref Order.Count; return r; }
        public object U() => new Order[2, 3].Length + new Customer[] { }.Length;
        public object V(object o) => ((Order)o).Total + (o as Customer)!.GetHashCode();
        public object W() { using (Res r = new Res()) return r; }
        public object X() => Box<Order>.Count + Box<Box<Customer>>.Count;
    }
    public class Res : System.IDisposable { public void Dispose() { } }
}
