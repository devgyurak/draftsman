using App;
namespace App.Web
{
    public class WithUsing
    {
        public object A() => new App.Models.Order();
        public object B() => new Boxes.Holder();
        public object C() => App.Models.Order.Count;
    }
}
namespace Other.Web
{
    public class Elsewhere
    {
        public object A() => new App.Models.Order();
        public object B() => new Boxes.Holder();
    }
}
