namespace Shop.Pat
{
    public class Attrs
    {
        public object A() { [Order] int Local() => 1; return Local(); }
        public object B() { System.Func<int> f = [Order] () => 1; return f; }
        public object C() { int Local([Order] int x) => x; return Local(1); }
        [Order] public object D() => 1;
    }
}
