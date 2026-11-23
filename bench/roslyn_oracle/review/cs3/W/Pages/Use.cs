using Lib2;
namespace W.Pages
{
    // Order.razor declares W.Pages.Order
    public class Use
    {
        public object M() => new Order();
        public object N() => Order.Count;
    }
}
