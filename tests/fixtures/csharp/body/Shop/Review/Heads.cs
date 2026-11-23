using LO = Lib.Order;
using Shop.Rev.Entities;

namespace Shop.Rev.Target.Lib
{
    public class Order
    {
        public static int Count;
    }
}

namespace Shop.Rev.Target.Sub
{
    // an alias's target is looked up where the alias is declared, at the top of the file:
    // Lib.Order, not the Shop.Rev.Target.Lib.Order the namespaces around the use would give
    public class Use
    {
        public class Lib
        {
            public class Order
            {
            }
        }

        public object A() => new LO();   //> LO=Lib.Order/t
        public object B() => LO.Count;   //> LO=Lib.Order/r
    }

    public class Generic<Lib>
    {
        public object A() => new LO();   //> LO=Lib.Order/t
    }
}

namespace Shop.Rev.Gen
{
    public class Lib<T>
    {
        public class Order
        {
            public static int Count;
        }
    }
}

namespace Shop.Rev.Gen.Sub
{
    // a first part written without type arguments is no Lib<T>: the namespace Lib further out
    public class Arity
    {
        public object A() => new Lib.Order();   //> Lib=- Order=Lib.Order/t
        public object B() => Lib.Order.Count;   //> Lib=- Order=Lib.Order/r
        public object C() => new Lib<int>.Order();   //> Lib=Shop.Rev.Gen.Lib/t Order=Shop.Rev.Gen.Lib.Order/t
    }
}

namespace Shop.Rev.Entities
{
    public class Models
    {
        public class Order
        {
            public static int Count;
        }
    }
}

namespace Web1
{
    // the global namespace Models comes before the class Models the file's using brings in
    public class FileUsing
    {
        public object A() => new Models.Order();   //> Models=- Order=Models.Order/t
        public object B() => Models.Order.Count;   //> Models=- Order=Models.Order/r
    }
}
