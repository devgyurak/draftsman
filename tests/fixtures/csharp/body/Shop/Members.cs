using Order = Lib.Order;

namespace Shop.Members;

// a compilation unit's alias comes after the namespaces around: Shop.Order; an event
// field hides a type as a field does; `case X X when`
public class Events
{
    public object M1() => Order.Max;   //> Order=Shop.Order/r
    public object M2() => new Order();   //> Order=Shop.Order/t
    public event System.Action? Customer;   //> Customer=-
    public void M3() => Customer.Invoke();   //> Customer=var/r
    public int M4(object o) { switch (o) { case Money Money when Money.Amount > 0: return 1; } return 0; }   //> Money=Shop.Money/t Money=- Money=var/r
}

// a record struct's parameters are its properties; a struct's primary constructor
// parameters are in scope in its members
public record struct Pos(int Customer)   //> Customer=-
{
    public int M() => Customer.GetHashCode();   //> Customer=var/r
}

public struct Holder(int Customer)   //> Customer=-
{
    public int M() => Customer.GetHashCode();   //> Customer=var/r
}

// a C# 14 extension block: its members are the static class's
public static class Extensions
{
    extension(Shop.Order o)   //> Shop=- Order=-
    {
        public static Shop.Order Fresh() => new Shop.Order();   //> Shop=- Order=- Shop=- Order=Shop.Order/t
    }
}
