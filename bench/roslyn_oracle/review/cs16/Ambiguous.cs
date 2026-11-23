using System.Collections.Generic;

namespace Shop.Amb
{
    public class Generic
    {
        static int G<T, U>(int x) => x;
        static object F(object a) => a;
        static object F(object a, object b) => a;
        public object A() => F(G<Order, Customer>(7));
        public object B(int a, int b, int c, int d) => F(a < b, c > d);
        public object B2(int Order, int b, int Customer, int d) => F(Order < b, Customer > d);
        public object C(object o) => o is Order ? 1 : 2;
        public object D(object o) => o is Order ? Order.Count : Customer.Count;
        public void E() { Box<Order> c = new Box<Order>(); }
        public object F2(object o) => (Customer)(o);
        public object G2(bool b) => (Flag)!b;
        public object H(int b) => (Mask)~b;
        public object I(object o) => o is Order o2 ? o2 : null!;
    }

    public unsafe class Pointers
    {
        public void A() { Point* p = null; }
        public void B() { Point * q; }
    }

    public class Collections
    {
        public int[] A() => [Order.Count, Customer.Count];
        public int[] B() => [.. Items.All, Order.Max];
        public int[] C(int[] xs) => xs[..Order.Count];
        public int[] D(int[] xs) => xs[Order.Count..];
        public System.Range E() => Order.Count..Order.Max;
        public List<Order> F() => [new Order()];
    }
}
