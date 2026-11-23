using O = Lib.Order;
namespace A.B
{
    using O = Lib2.Order;
    public class Inner
    {
        public object M() => new O();
        public object N() => O.Count;
    }
}
namespace A.C
{
    public class Outer
    {
        public object M() => new O();
        public object N() => O.Count;
    }
}
namespace A.D
{
    using P = Lib.Order;
    namespace E
    {
        public class Deep
        {
            public object M() => new P();
            public object N() => P.Count;
        }
    }
}
