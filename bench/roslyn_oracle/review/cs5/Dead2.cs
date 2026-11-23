namespace Shop.Dead2
{
    public class C
    {
#if false
        public object A() => 1;
#else
        public object A() => Order.Count;
#endif
#if !true
        public object B() => User.Count;
#endif
#if (false)
        public object C2() => User.Count;
#endif
#if false || false
        public object D() => User.Count;
#endif
#if true
        public object E() => Items.Count;
#else
        public object E() => User.Count;
#endif
#if DEBUG
        public object F() => Data.Count;
#endif
    }
}
