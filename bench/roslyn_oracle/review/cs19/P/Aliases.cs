using Order = Lib.Order;
using L = Lib;
using Map = System.Collections.Generic.Dictionary<string, Lib.Order>;

namespace Shop.Sub3
{
    public class A3
    {
        public Order O;
        public L.Order Q;
        public L::Order R;
        public Map M;
        public Cash C;
        public object Make() => new Order();
    }
}

namespace Other3
{
    public class B3
    {
        public Order O;
        public object Make() => new Order();
    }
}
