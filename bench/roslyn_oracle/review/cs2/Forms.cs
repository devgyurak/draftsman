using System;
using System.Linq;
using System.Collections.Generic;
namespace Shop.Forms
{
    public class Locals
    {
        public object A(int[] xs) => from Order in xs where Order.ToString() != "" select Order.GetHashCode();
        public object B(int[] xs) => from x in xs let Customer = x group Customer by Customer.ToString() into Money select Money.Key;
        public object C(int[] xs) => from x in xs join Order in xs on x equals Order into Customer select Customer.Count();
        public object D(int[] xs) => from int Money in xs select Money.ToString();
        public object E() { (int Order, int Customer) = (1, 2); return Order.ToString() + Customer.ToString(); }
        public object F() { var (Order, (Customer, c)) = (1, (2, 3)); return Order.ToString() + Customer.ToString(); }
        public object G(Dictionary<int, int> d) { if (d.TryGetValue(1, out int Order)) return Order.ToString(); return 0; }
        public object H() { try { } catch (Exception Order) when (Order.Message == "") { } return 0; }
        public object I() { for (int Order = 0; Order.CompareTo(1) < 0; Order++) { } return 0; }
        public unsafe object J(int[] xs) { fixed (int* Order = xs) { return Order->ToString(); } }
        public object K(object o) { switch (o) { case int Order when Order.CompareTo(1) > 0: return 1; case Status.Open: return 2; } return 0; }
        public object L() { int Customer(int x) => x; return Customer(1); }
        public object M(object o) => o is Cart { Customer: null } or Cart { Order: { Total: 1 } };
        public object N() => new Cart { Customer = Customer.Guest, Order = { Total = Order.Max } };
        public object O((int Order, int Customer) t) => t.Order + t.Customer + Order.Max;
        public object P() { var t = (Order: 1, Customer: 2); return t.Order; }
        public object R() { void L<Order>() { var x = typeof(Order); } return 0; }
        public object S(int Order) { Func<int> f = () => Order.GetHashCode(); return f; }
        public object T(object o) { if (o is not Order Customer) return 0; return Customer.Total; }
        public object U(IEnumerable<int> xs) { foreach (int Order in xs) { return Order.ToString(); } return Customer.Guest; }
        public object V() { { int Money = 1; } return 0; }
        public object W() => Money.Zero;
        public object X(Order Customer) => Customer.Customer.Name;
        public object Y() { using var Order = new System.IO.MemoryStream(); return Order.Length; }
    }
    public record Rec(Order Order, int Customer)
    {
        public object A() => Order.Max;
        public object B() => Order.Total;
        public object C() => Customer.GetHashCode();
    }
    public class Prim(Order Order)
    {
        public object A() => Order.Max;
    }
    public class PrimBase(int Customer) { public int X = Customer; }
    public class PrimDerived() : PrimBase(1)
    {
        public object A() => Customer.Guest;
    }
    public interface IHas { static int Money = 1; int Status { get; } }
    public class Impl : IHas
    {
        int IHas.Status => 1;
        public object A() => Money.Zero;
        public object B() => Status.Open;
    }
}
