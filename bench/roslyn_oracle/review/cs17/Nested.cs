namespace Shop.Amb
{
    public interface IThing
    {
        public struct Inner { public object A() => Order.Count; }
        object B() => Customer.Count;
        static object C => Order.Count;
    }
    public record Rec(int N)
    {
        public object A() => Order.Count;
        public record Sub(int M) : Rec(Customer.Count) { public object B() => Order.Count; }
    }
    public class Outer3
    {
        public class Mid { public class Leaf { public static object F = new Order(); public object G => Customer.Count; } }
        public System.Func<object> H = () => new Outer3.Mid.Leaf();
        static Outer3() { _ = Order.Count; }
        ~Outer3() { _ = Customer.Count; }
        public static Outer3 operator +(Outer3 a, Outer3 b) => Order.Count > 0 ? a : b;
        public static implicit operator int(Outer3 a) => Customer.Count;
        public object this[int i] { get => Order.Count; set => _ = Customer.Count; }
        public event System.Action Ev { add { _ = Order.Count; } remove { _ = Customer.Count; } }
        public Outer3(int x) : this() { _ = Order.Count; }
        public Outer3() { }
        public int P { get; init; } = Order.Count;
        public int Q => Customer.Count;
    }
}
