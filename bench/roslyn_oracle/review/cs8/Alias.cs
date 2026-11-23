using O = Shop.Outer;
using M = Shop.Models;
using G = Shop.Gen<int>;

namespace Shop.Aliased
{
    class B
    {
        void M1()
        {
            var a = new O.Mid.Leaf();
            var b = O.Mid.Leaf.N;
            var c = new M.Order();
            var d = M.Order.Count;
            var e = new G.Inner();
            var f = G.Inner.N;
        }
    }
}
