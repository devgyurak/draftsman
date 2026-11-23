namespace Shop
{
    public class Order { public static int Count = 1; public static int Max = 2; }
    public class Customer { public static int Count = 1; }
    public struct Point { public int X; }
    public class Box<T> { public static int Count; }
    public class Flag { public static explicit operator Flag(bool b) => new Flag(); }
    public class Mask { public static explicit operator Mask(int b) => new Mask(); }
    public class Items { public static int[] All = new int[3]; }
}
namespace Shop.Odd
{
    public class var { public static int Count; }
    public class dynamic { public static int Count; }
    public class nameof { public static int Count; }
    public class value { public static int Count; }
    public class field { public static int Count; }
}
