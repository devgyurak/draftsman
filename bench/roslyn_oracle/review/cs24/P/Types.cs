namespace Lib
{
    public class Order { public static Order Make() => new Order(); public class Line { } }
    public class Box<T> { }
    public class Box { }
    public class MarkAttribute : System.Attribute { }
    public static class Util { public static void Run() { } }
    namespace Sub { public class Deep { } }
}

namespace Shop
{
    public class Order { }
    public class L
    {
        public class Order { public static Order Make() => new Order(); public class Line { } }
        public class Box<T> { }
        public class Box { }
        public class MarkAttribute : System.Attribute { }
        public static class Util { public static void Run() { } }
        public class Sub { public class Deep { } }
    }
    public class G { public class Order { } public class Box<T> { } }
    public class M { public class Deep { } }
    public class LS { public class Deep { } }
}
