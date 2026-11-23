namespace Lib
{
    class Order { public static int Count = 1; }
    public class Customer { public static int Count = 1; }
    public class Base
    {
        class Money { }
        protected class Shown { public static int Count = 0; }
        private protected class Hidden { public static int Count = 0; }
        internal class Inner { public static int Count = 0; }
        int Status;
    }
}
namespace Lib2 { public class Order { public static int Count = 2; } }
namespace Shop
{
    public class Money { public static int Count = 0; }
    public class Hidden { public static int Count = 0; }
    public class Inner { public static int Count = 0; }
    public class Status { public static int Count = 0; }
    public class Shown { public static int Count = 0; }
    public class Data { public static int Count = 0; }
}
