namespace Shop.CC
{
    // the field's type is another Order: no Color Color, the name is the field
    public class OtherType
    {
        public global::Lib.Order Order = new global::Lib.Order();
        public object A() => Order.Total2;
        public object B() => Order.Max;
    }

    public class ArrayType
    {
        public Order[] Order = new Order[0];
        public object A() => Order.Length;
    }

    public class NullableStruct
    {
        public Money? Money = null;
        public object A() => Money.Value;
    }

    public class ListType
    {
        public System.Collections.Generic.List<Order> Order = new();
        public object A() => Order.Count;
    }
}
namespace Lib
{
    public class Base { public Order Order = new Order(); }
}
namespace Shop.CC
{
    // inherited from a base where `Order` is Lib.Order
    public class Derived : global::Lib.Base
    {
        public object A() => Order.Max;
        public object B() => Order.Total2;
    }

    public static class OrderExt { public static int Of(this Order o, int x) => x; }
    public class Ext
    {
        public Order Order = new Order();
        public object A() => Order.Of();
        public object B() => Order.Of(1);
    }
}
