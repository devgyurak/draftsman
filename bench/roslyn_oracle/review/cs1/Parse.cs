using System;
namespace Shop.Parse
{
    public class Cart { public Customer Customer = new Customer(); public Order Order = new Order(); }
    public class Casts
    {
        public int Order = 1;
        public Func<int, int> Handler = x => x;
        public int A() => (Order) - 1;
        public int C() => (Order) + 1;
    }
    public class Patterns
    {
        public bool A(Cart c) => c is { Customer.Name: "x" };
        public bool B(Cart c) => c is { Order.Total: 1 };
        public bool C(object o) => o is Cart { Customer: var Money } && Money.Name == "";
        public bool D(object o) => o is var Order && Order.ToString() == "";
        public bool E(int[] xs) => xs is [var Order, .. var Customer] && Order.ToString() == Customer.ToString();
        public bool F((int, int) p) => p is (var Order, var Customer) && Order.ToString() == Customer.ToString();
        public int G(object o) => o switch { var Order => Order.GetHashCode() };
    }
    public class Consts
    {
        const int Order = 1;
        public bool A(object x) => x is Order;
        public bool B(object x) => x is not Order;
        public bool C(int x) { const int Customer = 2; return x is Customer; }
    }
    public class TParams<Order>
    {
        public object A() => typeof(Order);
        public object B() => default(Order);
        public object C() => new System.Collections.Generic.List<Order>();
        public class Inner { public object A() => typeof(Order); }
        public object D<Customer>() => typeof(Customer);
    }
    public static class Exts
    {
        extension(int Customer)
        {
            public string M() => Customer.ToString();
        }
        extension<Order>(Order Money)
        {
            public string N() => Money.ToString() + typeof(Order);
        }
    }
    public class Lambdas
    {
        public Func<int, string> F = Order => Order.ToString();
        public object G = Order.Max;
        public Func<int, int, string> H = delegate (int Customer, int b) { return Customer.ToString(); };
        public object I() { Func<int, string> f = static Money => Money.ToString(); return f; }
        public object J() { foreach (var (Order, Customer) in new[] { (1, 2) }) { return Order.ToString() + Customer.ToString(); } return 0; }
    }
}
