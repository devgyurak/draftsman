using static G.Outer;

namespace Web6
{
    public class FileLevel
    {
        public object B1() => new Box();
        public object B2() => Box.Count;
        public object B3() => new Lib.Order();
        public object B4() => Lib.Order.Count;
    }
}

namespace Web7
{
    using G;
    public class BlockLevel
    {
        public object C1() => new Box();
        public object C2() => Box.Count;
        public object C3() => new Box<int>();
    }
}

namespace Web8
{
    using static G.Outer;
    public class StaticBlock
    {
        public object D1() => new Lib.Order();
        public object D2() => Lib.Order.Count;
        public object D3() => new Lib<int>.Order();
    }
}
