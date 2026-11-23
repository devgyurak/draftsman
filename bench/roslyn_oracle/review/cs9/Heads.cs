using App;
using App.Entities;

namespace Web1
{
    public class FileUsing
    {
        public object A() => new Models.Order();
        public object B() => Models.Order.Count;
    }
}
namespace Web2
{
    using App.Entities;
    public class BlockUsing
    {
        public object A() => new Models.Order();
        public object B() => Models.Order.Count;
        public object C() => typeof(Models.Order);
    }
}
namespace App.Web
{
    public class Forms
    {
        public object A() => typeof(Models.Order);
        public object B(object o) => o is Models.Order;
        public object C() => new System.Collections.Generic.List<Models.Order>();
        public object D() => new Models.Order[0];
        public object E(object o) => (Models.Order)o;
        public object F() => nameof(Models.Order);
        public object G() => default(Models.Order);
        public object H() => new Models.Order.Line();
        public object I() => Models.Order.Line.Count;
        public object J() => new global::Models.Order();
        public object K() => global::Models.Order.Count;
        public object L() => new Deep.Models.Order();
        public object M() => Deep.Models.Order.Count;
        public object N() => new App.Models.Order();
        public Models.Order Field = new Models.Order();
    }
    public class Fields
    {
        public Boxes.Holder Models = new Boxes.Holder();
        public object A() => Models.Order.Count;
        public object B() => new Models.Order();
    }
    public class Params
    {
        public object A(Boxes.Holder Models) => Models.Order.Count;
        public object B() { var Models = new Boxes.Holder(); return Models.Order.Count; }
        public object C() { Boxes.Holder Deep = new Boxes.Holder(); return Deep.Order.Count; }
    }
    public class Outer
    {
        public class Models { public class Order { public static int Count; } }
        public class In
        {
            public object A() => new Models.Order();
            public object B() => Models.Order.Count;
        }
    }
    public class WithBase { public class Models { public class Order { public static int Count; } } }
    public class Derived : WithBase
    {
        public object A() => new Models.Order();
        public object B() => Models.Order.Count;
    }
}
namespace G.Sub
{
    public class Arity
    {
        public object A() => new Lib.Order();
        public object B() => Lib.Order.Count;
        public object C() => new Lib<int>.Order();
        public object D() => Lib<int>.Order.Count;
    }
}
