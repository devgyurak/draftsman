using Arr = Shop.Order[];
using Tup = (Shop.Order, int);
using Lst = System.Collections.Generic.List<Shop.Customer>;
namespace Shop.Amb
{
    public class AliasAny
    {
        public object A() { Arr xs = new Shop.Order[1]; return xs; }
        public object B() { Tup t = (new Order(), 1); return t; }
        public object C() => new Lst();
        public object D() => typeof(Arr);
        public object E() => Lst.Equals(null, null);
    }
}
