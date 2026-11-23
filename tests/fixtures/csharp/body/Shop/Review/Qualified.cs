namespace Models
{
    public class Order
    {
        public static int Count;
    }
}

namespace Shop.Rev.Models
{
    public class Order
    {
        public static int Count;
    }
}

namespace Shop.Rev.Web
{
    // the first part of a qualified name is looked up as a simple name: the namespace
    // Shop.Rev.Models around comes before the global Models
    public class Page
    {
        public object A() => new Models.Order();   //> Models=- Order=Shop.Rev.Models.Order/t
        public object B() => Models.Order.Count;   //> Models=- Order=Shop.Rev.Models.Order/r
    }
}

namespace Shop.Rev.Qual
{
    public class Lib
    {
        public class Order
        {
            public static int Count;
        }
    }
}

namespace Shop.Rev.Qual.Sub
{
    // the class Shop.Rev.Qual.Lib is nearer than the namespace Lib
    public class Use
    {
        public object A() => new Lib.Order();   //> Lib=Shop.Rev.Qual.Lib/t Order=Shop.Rev.Qual.Lib.Order/t
        public object B() => typeof(Lib.Order);   //> Lib=Shop.Rev.Qual.Lib/t Order=Shop.Rev.Qual.Lib.Order/t
        public object C() => Lib.Order.Count;   //> Lib=Shop.Rev.Qual.Lib/r Order=Shop.Rev.Qual.Lib.Order/r
    }
}
