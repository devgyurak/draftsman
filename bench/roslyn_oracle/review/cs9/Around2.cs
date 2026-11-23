using Shop;
namespace System
{
    namespace Mine4
    {
        public class NestedBlocks
        {
            public object A() => new Random();
            public object B() => Order.Count;
        }
    }
    public class Clock2 { public static int Count; }
}
namespace System.Mine5
{
    public class Outer
    {
        public class Random { public static int Count; }
        public object A() => Random.Count;
        public object B() => Clock2.Count;
    }
    public class FromBase : Shop.Base
    {
        public object A() => Random.Count;
    }
    public class Arity
    {
        public object A() => Random<int>.Count;
        public object B() => new Random<int>();
    }
}
namespace System.Collections.Generic.Mine
{
    public class Arity0
    {
        public object A() => List.Count;
        public object B() => new List<int>();
    }
}
