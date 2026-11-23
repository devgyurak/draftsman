using System.Collections.Generic;
namespace App.Web
{
    public class Ctl : Microsoft.AspNetCore.Mvc.ControllerBase
    {
        public object A() => User.Identity.Name;
    }
    public class FromBase : Boxes.WithField
    {
        public object A() => Models.Order.Count;
    }
    public partial class Part
    {
        public object A() => Models.Order.Count;
    }
    public partial class Part
    {
        public Boxes.Holder Models = new Boxes.Holder();
    }
    public class Locals
    {
        public object A(List<Boxes.Holder> xs) { foreach (var Models in xs) return Models.Order.Count; return 0; }
        public object B(List<Boxes.Holder> xs) => xs.ConvertAll(Models => Models.Order.Count);
        public object C(object o) => o is Boxes.Holder Models ? Models.Order.Count : 0;
        public object D(Dictionary<int, Boxes.Holder> d) => d.TryGetValue(1, out var Models) ? Models.Order.Count : 0;
        public object E() { var (Models, n) = (new Boxes.Holder(), 1); return Models.Order.Count; }
        public object F() => Models.Order.Count;
    }
}
namespace App.Web2
{
    using static Boxes.Statics;
    public class BlockStatic
    {
        public object A() => Models.Order.Count;
    }
}
