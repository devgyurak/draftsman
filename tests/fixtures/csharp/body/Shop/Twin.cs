namespace Shop;

// compiled for net11.0 and net10.0: where the two resolve a name differently, "split"
public class Twin
{
#if NET11_0_OR_GREATER
    public class Order
    {
    }
#endif

    public object M() => new Order();   //> Order=split/t

#if DEBUG
    public object D() => new Customer();   //> Customer=Shop.Customer/t
#else
    public object D() => new Money(0);
#endif
}
