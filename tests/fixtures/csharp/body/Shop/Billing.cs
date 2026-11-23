namespace Shop.Billing
{
    public class Invoice
    {
    }
}

namespace Shop.Other
{
    using Lib;

    // a using inside a namespace block comes before the namespaces around it
    public class Near
    {
        public object M() => new Order();   //> Order=Lib.Order/t
        public object N() => new Invoice();   //> Invoice=Lib.Invoice/t
        public object R() => Receipt.Print();   //> Receipt=Lib.Extra.Receipt/r
    }
}
