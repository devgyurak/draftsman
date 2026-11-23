namespace Lib
{
    public class Order
    {
        public static int Count => 0;
    }

    public class Invoice
    {
    }

    public class Box
    {
    }

    public static class Defaults
    {
        public static int Customer = 1;
        public static int Money = 2;
    }
}

namespace Lib.Extra
{
    public class Receipt
    {
        public static Receipt Print() => new Receipt();   //> Receipt=- Receipt=Lib.Extra.Receipt/t
    }
}
