using Lib2;
namespace Lib.Sub
{
    // Lib.Order has no modifier: internal to L
    public class Use
    {
        public object M() => new Order();
        public object N() => Order.Count;
    }
}
