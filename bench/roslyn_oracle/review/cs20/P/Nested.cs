namespace A
{
    using O = Lib.Order;

    namespace B
    {
        public class X
        {
            public O F;
            public object M() => new O();
        }
    }

    public class W
    {
        public O F;
    }
}

namespace A.B
{
    public class Y
    {
        public O F;
        public object M() => new O();
    }
}

namespace Shop.Inner
{
    public class Z
    {
        public Cash C;
        public Safe S;
    }
}

namespace Elsewhere
{
    public class V
    {
        public Cash C;
        public object M() => new Cash();
    }
}
