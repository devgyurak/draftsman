namespace Lib { public class Order { public static int Count; } }
namespace Lib2 { public class Order { public static int Count; } }
namespace A.Lib { public class Order { public static int Count; } }
namespace G { public class Lib<T> { public class Order { public static int Count; } } }
namespace App.Models { public class Order { public static int Count; } }
namespace App.User { public class Identity { public static int Name; } }
namespace Boxes
{
    public class Holder { public OrderBox Order = new OrderBox(); }
    public class OrderBox { public int Count; }
    public static class Statics { public static Holder Models = new Holder(); }
    public class WithField { public Holder Models = new Holder(); }
}
