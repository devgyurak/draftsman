namespace Lib { public class Order { public static int Count; } }
namespace A.Lib { public class Order { public static int Count; } }
namespace A.B.Lib { public class Order { public static int Count; } }
namespace G
{
    public class Lib<T> { public class Order { public static int Count; } }
    public class Box<T> { public static int Count; }
    public static class Outer { public class Lib<T> { public class Order { public static int Count; } } }
}
public class Box { public static int Count; }
