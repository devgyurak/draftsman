using Shop;
using Task = System.Threading.Tasks.Task;
namespace Other.Al
{
    public class Top
    {
        public object A() => Task.CompletedTask;
        public object B() { Task t = null; return t; }
    }
}
namespace Shop.Al
{
    using Order = System.Int32;
    public class Block
    {
        public object A() => Order.MaxValue;
        public object B() { Order t = 1; return t; }
    }
}
namespace Shop.Gen
{
    public class Base<T> { public class Entry { public static int Count = 0; } }
    public class Derived : Base<int>
    {
        public object A() => new Entry();
        public object B() => Entry.Count;
    }
}
namespace Shop.Outer
{
    using Lib;
    namespace In
    {
        // Shop.Order is found in Shop before the usings of Shop.Outer? No: Shop.Outer's using comes first
        public class Deep
        {
            public object A() => new Order();
            public object B() => Order.Count;
        }
    }
}
