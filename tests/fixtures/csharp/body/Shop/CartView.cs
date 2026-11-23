namespace Shop;

public partial class Cart
{
    public string M() => Order.ToString();   //> Order=var/r
    public Order N() => new Order();   //> Order=- Order=Shop.Order/t
}

// a nested type inherited from a supertype; a type parameter
public class Special : Order
{
    public object M() => new Line();   //> Line=Shop.Order.Line/t
    public object N() => Line.Make();   //> Line=Shop.Order.Line/r
}

public class Box<Customer>
{
    public Customer? Get() => default(Customer);   //> Customer=- Customer=tparam/t
}

// a method named like a type does not hide it where only a type stands
public class Methods
{
    public void Customer() { }
    public object M() { Customer c = new Customer(); return c; }   //> Customer=Shop.Customer/t Customer=Shop.Customer/t
}
