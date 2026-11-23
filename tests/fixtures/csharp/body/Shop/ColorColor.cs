namespace Shop;

// a field whose type has its name (`Order Order`): before a static member or a nested
// type the name is the type, before an instance member the field; with a static and an
// instance overload (`Of()`, `Of(int)`) the call decides
public class Holder2
{
    public Order Order = new Order();   //> Order=- Order=- Order=Shop.Order/t

    public object A() => Order.Max;   //> Order=Shop.Order/r
    public object B() => Order.Total;   //> Order=var/r
    public object C() => Order.Line.Make();   //> Order=Shop.Order/r Line=Shop.Order.Line/r
    public object D() => Order.Of();   //> Order=Shop.Order/r
    public object E() => Order.Of(1);   //> Order=var/r

    public class Inner
    {
        public object M() => Order.Max;   //> Order=Shop.Order/r
    }
}
