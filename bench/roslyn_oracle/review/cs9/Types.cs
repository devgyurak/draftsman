namespace Shop
{
    public class Order { public static int Count; }
    public class Money { public static int Count; }
    public class Host { public static int Count; }
    public class Random { public static int Count; }
    public class Random<T> { public static int Count; }
    public class List { public static int Count; }
    public class Holder
    {
        public class Random { public static int Count; }
        public class Encoder { public static int Count; }
    }
    public class Base { public class Random { public static int Count; } }
}
namespace Models { public class Order { public static int Count; public class Line { public static int Count; } } }
namespace App.Models { public class Order { public static int Count; public class Line { public static int Count; } } }
namespace App.Entities { public class Models { public class Order { public static int Count; } } }
namespace Lib { public class Order { public static int Count; } }
namespace G { public class Lib<T> { public class Order { public static int Count; } } }
namespace Deep.Models { public class Order { public static int Count; } }
namespace App.Deep.Models { public class Order { public static int Count; } }
namespace Boxes
{
    public class Holder { public OrderBox Order = new OrderBox(); }
    public class OrderBox { public int Count; }
}
