using Lib;

namespace Shop.Signatures;

// an operator's, an indexer's and a conversion's parameters hide in their bodies; a
// verbatim identifier is its name without the @; `Box` with no type argument is no
// Shop.Box<Customer>, whose arity is 1: Roslyn goes on to Lib.Box
public class Ops
{
    public static Ops operator +(Ops a, int Customer) => Customer.ToString() == "" ? a : a;   //> Ops=- Ops=- Customer=- Customer=var/r
    public string this[int Order] => Order.ToString();   //> Order=- Order=var/r
    public static explicit operator int(Ops Customer) => Customer.GetHashCode();   //> Ops=- Customer=- Customer=var/r
    public string V() { var @Order = 1; return Order.ToString(); }   //> Order=- Order=var/r
    public object B() => new Box();   //> Box=Lib.Box/t
    public object C() => new Box<Order>();   //> Box=Shop.Box/t Order=Shop.Order/t
}
