namespace Shop
{
    public class Outer { public class Mid { public class Leaf { public static int N; } } }
    public class Gen<T> { public class Inner { public static int N; } }
    public class Gen { public class Inner { public static int N; } }
    public class Order { public static int Count; public static Order Make() => new Order(); }
    public class Host { public static int Run() => 0; }
    public class RelayCommand { }
    public static class Tools { public static int Max = 1; public class Item { } }
    public class Program { public static void Main() { } }
}
namespace Shop.Models { public class Order { public static int Count; } }
namespace Other { public class Outer { public class Mid { public class Leaf { public static int N; } } } }
