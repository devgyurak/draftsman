namespace Shop.Parts
{
    public partial class Split
    {
        public object A() => nameof(Order);
        public object B() => nameof(Customer);
        public object C() => new Order.Line();
    }
    public partial class Whole
    {
        public object A() => Money.GetHashCode();
    }
    public class Base
    {
        public int Util;
        public class Task { }
        public static int Status;
    }
    public class Outer : Base
    {
        public class Inner
        {
            public object A() => new Task();
            public object B() => nameof(Status);
        }
    }
}
