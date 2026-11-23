global using Receipt = Lib2.Receipt;
namespace Shop
{
    public class Order
    {
        public static int Max = 1;
        public static int Count = 2;
        public decimal Total;
        public Customer Customer = new Customer();
        public class Line { public static int N = 1; }
    }
    public class Customer { public static Customer Guest = new Customer(); public string Name = ""; public static int Count = 0; }
    public struct Money { public static Money Zero; public int Amount; public static int Count = 0; }
    public enum Status { Open, Closed }
    public class Task { public static int Count = 0; }
    public class Ord { public static int Count = 0; }
    public class Invoice { public static int Count = 0; }
    public class Receipt { public static int Count = 0; }
    public class Util { public static int Count = 0; }
    public class Cart { public Customer Customer = new Customer(); public Order Order = new Order(); }
}
namespace Lib
{
    public class Order { public static int Count = 7; }
    public class Invoice { public static int Count = 7; }
    public class Receipt { public static int Count = 7; }
}
namespace Lib2
{
    public class Order { public static int Count = 8; }
    public class Invoice { public static int Count = 8; }
    public class Receipt { public static int Count = 8; }
}
