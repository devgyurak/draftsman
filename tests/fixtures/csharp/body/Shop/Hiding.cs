using System;
using System.Collections.Generic;
using System.Linq;
using O = Shop.Order;

namespace Shop;

public class Base
{
    protected int Customer;
    public static Order Order => Order.Create();   //> Order=- Order=- Order=Shop.Order/r
}

// what hides a type where an expression stands, and what does not
public class Hiding : Base
{
    public Money Money { get; } = Money.Zero;   //> Money=- Money=- Money=Shop.Money/r
    public Point Point;
    public string Status = "";

    public void Locals(int Order)   //> Order=-
    {
        var a = Order.ToString();   //> Order=var/r
        Order b = null!;   //> Order=Shop.Order/t
    }

    public void Members()
    {
        var a = Money.Zero;   //> Money=Shop.Money/r
        var b = Money.Amount;   //> Money=var/r
        var c = Point.X;   //> Point=var/r
        var d = Status.Length;   //> Status=var/r
        var e = Customer.ToString();   //> Customer=var/r
        Status f = Shop.Status.Open;   //> Status=Shop.Status/t Shop=- Status=Shop.Status/r
        var g = Order.Max;   //> Order=Shop.Order/r
        var h = Order.Total;   //> Order=var/r
    }

    public void Binders(List<Order> orders, object o)   //> Order=-
    {
        foreach (var Customer in orders) { var a = Customer.Total; }   //> Customer=- Customer=var/r
        var b = orders.Select(Order => Order.Total);   //> Order=- Order=var/r
        var c = from Point in orders select Point.Total;   //> Point=- Point=var/r
        if (o is Order Money) { var d = Money.Total; }   //> Order=Shop.Order/t Money=- Money=var/r
        if (int.TryParse("1", out var Util)) { var e = Util.ToString(); }   //> Util=- Util=var/r
        try { } catch (OrderException Status) { var f = Status.Message; }   //> OrderException=Shop.OrderException/t Status=- Status=var/r
        using var Repo = new System.IO.MemoryStream();   //> Repo=-
        var g = Repo.Length;   //> Repo=var/r
        var (Line, n) = (1, 2);   //> Line=-
        var h = Line.ToString();   //> Line=var/r
    }

    public T Generic<Customer, T>(Customer x) where T : new() => new T();   //> Customer=- Customer=- T=- T=- T=- T=tparam/t
}

// a nested type before the namespace's; an alias
public class Nesting
{
    public void M()
    {
        var a = new Order();   //> Order=Shop.Nesting.Order/t
        var b = Order.Make();   //> Order=Shop.Nesting.Order/r
        var c = O.Create();   //> O=Shop.Order/r
        O d = new O();   //> O=Shop.Order/t O=Shop.Order/t
    }

    public class Order
    {
        public static int Make() => 0;
    }
}

// a primary constructor's parameters are in scope in the whole body
public class Service(Customer Customer, int Order)   //> Customer=- Customer=- Order=-
{
    public string Name => Customer.Name;   //> Customer=var/r
    public Customer Guest => Customer.Guest;   //> Customer=- Customer=Shop.Customer/r
    public int Max() => Order.ToString().Length;   //> Order=var/r
}

// a constant beside a type: `is X` looks for the type first; a pattern (`or`, `not`, a
// switch arm) and a case label look for the constant
public class Constants
{
    public const int Order = 1;

    public bool M(object o) => o is Order;   //> Order=Shop.Order/t
    public bool N(object o) => o switch { Order => true, _ => false };   //> Order=var/r
    public bool K(object o) { switch (o) { case Order: return true; } return false; }   //> Order=var/r
    public bool L(object o) => o is Order or Customer;   //> Order=var/r Customer=Shop.Customer/r
    public bool J(object o) => o is not Customer;   //> Customer=Shop.Customer/r
}
