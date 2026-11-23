namespace Shop
{
    public class Order { public static int Count; public int Total; public const int Max = 9; }
    public class Customer { public static int Count; public const int Min = 1; }
    public enum Status { Open, Closed }
    public class Box<T> { public static int Count; }
}
