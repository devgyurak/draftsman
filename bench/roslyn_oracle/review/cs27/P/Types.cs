namespace Lib
{
    public class Order { public static Order Make() => new Order(); }
    public class Box<T> { }
    namespace Sub { public class Deep { public static int Count; } }
}
