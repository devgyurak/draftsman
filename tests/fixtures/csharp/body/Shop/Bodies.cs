using System;
using System.Collections.Generic;

namespace Shop;

// every kind of body, and the names in a body that are no name of the scope
public class Bodies : Base
{
    private readonly Func<Order> make = () => new Order();   //> Order=- Order=Shop.Order/t
    private Money zero = Money.Zero;   //> Money=- Money=Shop.Money/r
    public event EventHandler? Changed { add { _ = new Point(); } remove { } }   //> Point=Shop.Point/t
    static Bodies() { _ = new Money(1); }   //> Money=Shop.Money/t

    public Bodies() : this(new Order())   //> Order=Shop.Order/t
    {
    }

    public Bodies(Order o)   //> Order=-
    {
    }

    public Order this[int i] => new Order();   //> Order=- Order=Shop.Order/t

    public Status State   //> Status=-
    {
        get { return Status.Open; }   //> Status=Shop.Status/r
        set { _ = value == Status.Closed; }   //> Status=Shop.Status/r
    }

    public static Bodies operator +(Bodies a, Bodies b) => new Bodies(new Order());   //> Bodies=- Bodies=- Bodies=- Bodies=Shop.Bodies/t Order=Shop.Order/t
    public static explicit operator Order(Bodies b) => new Order();   //> Order=- Order=Shop.Order/t
    ~Bodies() { _ = Util.Version; }   //> Util=Shop.Util/r

    // not a body: attributes, parameter defaults, signatures
    [Obsolete(nameof(Order))]   //> Order=-
    public void Signature(Status s = Status.Open)   //> Status=- Status=-
    {
        [Obsolete(nameof(Customer))] void Local() { }   //> Customer=-
    }

    // names after a dot, named arguments, initializers' and patterns' members, tuple
    // element names: no name of the scope
    public void NotScope(Holder h)
    {
        var a = h.Order;   //> Order=-
        var b = h?.Order;   //> Order=-
        var c = Take(Order: 1);   //> Order=-
        var d = new Holder { Order = null };   //> Holder=Shop.Holder/t Order=-
        var e = new { Order = 1, Customer = 2 };   //> Order=- Customer=-
        var f = (Order: 1, Customer: 2);   //> Order=- Customer=-
        var g = h with { Order = null };   //> Order=-
        var i = h is { Order: null };   //> Order=-
        var j = this.Customer;   //> Customer=-
        var k = base.Customer;   //> Customer=-
        Point: Take(1);   //> Point=-
        goto Point;   //> Point=-
    }

    public static int Take(int Order) => Order;   //> Order=- Order=-
}

public record Holder
{
    public Order? Order { get; init; }   //> Order=- Order=-
}

public class Derived(Order o) : Bodies(new Order())   //> Order=- Order=Shop.Order/t
{
}
