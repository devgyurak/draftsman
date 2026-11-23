namespace Shop.Rev.Acc
{
    public class A
    {
        private class Order { }
        private class Customer { public static int Guest = 0; }
        protected class Handler { public static int Count = 1; }
        private protected class Kind { public static int Count = 1; }
        private int Money = 0;
    }

    // a private nested type or field of the base is no member of a subclass: Shop's Order,
    // Customer and Money; a protected one is
    public class B : A
    {
        public object M() => new Order();   //> Order=Shop.Order/t
        public object N() => Customer.Guest;   //> Customer=Shop.Customer/r
        public object P() => Handler.Count;   //> Handler=Shop.Rev.Acc.A.Handler/r
        public object Q() => Kind.Count;   //> Kind=Shop.Rev.Acc.A.Kind/r
        public object R() => Money.Zero;   //> Money=Shop.Money/r
    }
}
