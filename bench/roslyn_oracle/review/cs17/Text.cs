namespace Shop.Amb
{
    public class Text
    {
        public object A() { var s = @"
#if false
"; return Order.Count; }
        public object B() => Customer.Count;
        public object C() { var s = """
            #endif
            #else
            """; return Order.Count; }
        /*
#if false
        */
        public object D() => Customer.Count;
        /*
#endif
        */
        public object E() => Order.Count;
    }
}
