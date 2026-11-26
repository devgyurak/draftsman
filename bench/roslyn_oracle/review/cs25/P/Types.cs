namespace Lib
{
    public interface IThing { }
    public class Order
    {
        public Order() { }
        public Order(int n) { }
        public static Order Make() => new Order();
        public const int Max = 1;
        public class Line { public static Line Make() => new Line(); }
    }
    public class Box<T> { public static Box<T> Make() => new Box<T>(); }
    public class Box { }
    public enum Kind { A, B }
    public static class Util { public static void Run() { } public static T Id<T>(T x) => x; }
    public class MarkAttribute : System.Attribute { public MarkAttribute() { } public MarkAttribute(System.Type t) { } }
    public record Rec(int N);
    namespace Sub { public class Deep { public static int Count; } }
}

namespace Shop
{
    public class L
    {
        public interface IThing { }
        public class Order
        {
            public Order() { }
            public Order(int n) { }
            public static Order Make() => new Order();
            public const int Max = 1;
            public class Line { public static Line Make() => new Line(); }
        }
        public class Box<T> { public static Box<T> Make() => new Box<T>(); }
        public class Box { }
        public enum Kind { A, B }
        public static class Util { public static void Run() { } public static T Id<T>(T x) => x; }
        public class MarkAttribute : System.Attribute { public MarkAttribute() { } public MarkAttribute(System.Type t) { } }
        public record Rec(int N);
        public class Sub { public class Deep { public static int Count; } }
    }
    public class G { public class Order { } }
    public class M { public class Deep { public static int Count; } }
    public class Lib { public class Order { public static Order Make() => new Order(); } public enum Kind { A, B } }
}
