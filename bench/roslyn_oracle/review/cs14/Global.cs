using Lib2;
namespace Other.G
{
    public class GlobalFirst
    {
        public object A() => new Order();
        public object B() => Order.Count;
    }
}
