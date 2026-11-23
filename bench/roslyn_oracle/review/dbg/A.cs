namespace App.Web
{
    public class NoUsing
    {
        public object A() => new App.Models.Order();
        public object B() => new Boxes.Holder();
        public object C() => App.Models.Order.Count;
    }
}
