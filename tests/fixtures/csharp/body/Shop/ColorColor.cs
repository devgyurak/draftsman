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

// a field of another type of the name (Lib's Order, inherited): the name is the field
public class OtherOrder : Lib.OrderHolder
{
    public object A() => Order.Create();   //> Order=var/r
}

// `Spot? Spot` is a Nullable<Spot>: no Color Color
public struct Spot
{
    public static int Value = 1;
}

public class SpotHolder
{
    public Spot? Spot;
    public object A() => Spot.Value;   //> Spot=var/r
}

// an extension method of the name may make the call an instance one
public class Stamp
{
    public static int Make() => 0;
}

public static class StampExtensions
{
    public static int Make(this Stamp s, int x) => x;
}

public class StampHolder
{
    public Stamp Stamp = new Stamp();   //> Stamp=- Stamp=- Stamp=Shop.Stamp/t
    public object A() => Stamp.Make(1);   //> Stamp=var/r
}
