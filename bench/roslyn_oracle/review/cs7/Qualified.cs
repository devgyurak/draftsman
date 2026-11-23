namespace App.Web
{
    // `Models` is App.Models, nearer than the global namespace Models
    public class Near
    {
        public object A() => new Models.Order();
        public object B() => Models.Order.Count;
    }
}
namespace Shop.Sub
{
    // `Lib` is the class Shop.Lib, nearer than the namespace Lib
    public class Class
    {
        public object A() => new Lib.Order();
        public object B() => Lib.Order.Count;
    }
    public class Prop
    {
        public Shop.Lib Lib = new Shop.Lib();
        public object A() => new Lib.Order();
        public object B() => typeof(Lib.Order);
    }
}
