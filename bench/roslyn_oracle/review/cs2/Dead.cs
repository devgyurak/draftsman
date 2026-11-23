namespace Shop.Dead
{
    public class Never
    {
#if false
        public object A() => new Order();
#endif
#if NEVER_DEFINED
        public object B() => Customer.Guest;
#else
        public object B() => 1;
#endif
#if !DEBUG
        public object C() => Money.Zero;
#endif
        public object D() => Status.Open;
    }
}
