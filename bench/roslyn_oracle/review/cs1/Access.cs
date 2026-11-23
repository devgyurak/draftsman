namespace Shop.Acc
{
    public class A
    {
        private class Order { }
        private class Customer { public static int Guest = 0; }
        protected class Handler { }
    }

    // a private nested type of the base is not accessible: Shop.Order, Shop.Customer
    public class B : A
    {
        public object M() => new Order();
        public object N() => Customer.Guest;
        public object P() => new Handler();
    }
}
