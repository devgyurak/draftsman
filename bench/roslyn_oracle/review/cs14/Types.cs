namespace Shop
{
    public class Order { public static int Count; public int Total; }
    public class Money { public static int Count; }
    public class Status { public static int Count; }
    public class OrderAttribute : System.Attribute { }
    public class Holder { public Box Order = new Box(); public Box Money = new Box(); }
    public class Box { public int Count; public int Total; }
}
public class Order { public static int Count; }
namespace Lib2 { public class Order { public static int Count; } }
