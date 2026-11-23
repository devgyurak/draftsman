namespace Web5
{
    using G;
    public class ViaUsing
    {
        public object A() => new Lib.Order();
        public object B() => Lib.Order.Count;
        public object C() => new Lib<int>.Order();
        public object D() => Lib<int>.Order.Count;
    }
}
