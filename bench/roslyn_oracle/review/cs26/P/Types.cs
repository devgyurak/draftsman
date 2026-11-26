namespace Lib
{
    public class Order { public static Order Make() => new Order(); }
    public class Box<T> { }
    namespace Sub { public class Deep { public static int Count; } }
}
namespace Shop
{
    public class M { public class Deep { public static int Count; } }
    public class N { public class Deep { public static int Count; } public class Order { } }
    public class Lib { public class Order { } public class Sub { public class Deep { } } }
}
