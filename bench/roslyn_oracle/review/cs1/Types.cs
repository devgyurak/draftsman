namespace Shop
{
    public class Order
    {
        public static int Max = 1;
        public static int Total2 = 2;
        public static int Length = 3;
        public decimal Total;
        public static Order Of() => new Order();
        public class Line { public static int N = 1; }
    }
    public class Customer { public static Customer Guest = new Customer(); public string Name = ""; }
    public struct Money { public static int Value = 1; public static Money Zero; public int Amount; }
    public enum Status { Open, Closed }
    public class Handler { public static int Count = 0; }
    public class Task { public static int Count = 0; }
    public class Error { public static int Count = 0; public static void WriteLine() { } }
    public class Helper { public static int Count = 0; }
    public enum EntityKind { Order, Customer }
}
namespace Lib
{
    public class Order { public int Total2 = 5; public int Max = 6; public static int Count = 7; }
    public class Helper { public static int Count = 1; }
    public class Invoice { }
}
namespace Lib2
{
    public class Order { public static int Count = 8; }
}
namespace Shop.Lib
{
    public class Order { public static int Count = 9; }
}
