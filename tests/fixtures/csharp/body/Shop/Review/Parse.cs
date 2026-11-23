namespace Shop.Rev.Parse
{
    // `(Order) - 1` subtracts from a field: a name in parentheses before `-` or `+` is no cast
    public class Casts
    {
        public int Order = 1;
        public int A() => (Order) - 1;   //> Order=-
        public int B() => (Order) + 1;   //> Order=-
    }

    public class Holder
    {
        public Customer Customer = null!;
        public Order Order = null!;
    }

    // a property pattern's path starts at a member
    public class Patterns
    {
        public bool A(Holder c) => c is { Customer.Name: "x" };   //> Holder=- Customer=var/r Name=-
        public bool B(Holder c) => c is { Order.Total: 1 };   //> Holder=- Order=var/r Total=-
    }

    // an extension block's receiver is a parameter of its members, its type parameter a
    // type there
    public static class Exts
    {
        extension(int Customer)   //> Customer=-
        {
            public string M() => Customer.ToString();   //> Customer=var/r
        }
        extension<Order>(Order Money)   //> Order=- Order=- Money=-
        {
            public string N() => Money.ToString() + typeof(Order);   //> Money=var/r Order=tparam/t
        }
    }
}
