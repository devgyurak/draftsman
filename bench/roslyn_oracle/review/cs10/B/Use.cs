namespace App.Web
{
    public class Use
    {
        public object A() => new Models.Order();
        public object B() => Models.Order.Count;
        public object C() => new Models2.Order();
        public object D() => Models2.Order.Count;
        public object E() => Shared.Count;
    }
}
