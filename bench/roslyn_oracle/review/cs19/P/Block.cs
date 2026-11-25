namespace Shop.Sub4
{
    using Order = Lib.Order;

    public class C4
    {
        public Order O;
        public object Make() => new Order();
    }
}

namespace Shop.Sub4
{
    public class D4
    {
        public Order O;
        public Cash C;
        public object Make() => new Order();
    }
}
