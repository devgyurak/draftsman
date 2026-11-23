using Lib2;
namespace Lib.Sub
{
    // Lib.Order is internal to L: from B the name is Lib2.Order
    public class Use
    {
        public object M() => new Order();
        public object N() => Order.Count;
        public object P() => Customer.Count;
    }
}
