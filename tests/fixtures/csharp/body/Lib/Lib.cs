namespace Lib
{
    public class Order
    {
        public static int Count => 0;
    }

    public class Invoice
    {
    }
}

namespace Lib.Extra
{
    public class Receipt
    {
        public static Receipt Print() => new Receipt();   //> Receipt=- Receipt=Lib.Extra.Receipt/t
    }
}
