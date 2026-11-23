using System;
using System.Collections.Generic;
using System.Linq;

namespace Shop;

// where only a type can stand (t), and where an expression does (r)
public class Positions
{
    public object M(object o, List<Order> orders)
    {
        Order a = new Order();   //> Order=Shop.Order/t Order=Shop.Order/t
        var b = (Order)o;   //> Order=Shop.Order/t
        var c = o as Order;   //> Order=Shop.Order/t
        var t = typeof(Order);   //> Order=Shop.Order/t
        bool d = o is Order;   //> Order=Shop.Order/t
        if (o is Order e) { }   //> Order=Shop.Order/t
        var f = default(Point);   //> Point=Shop.Point/t
        var g = new List<Customer>();   //> Customer=Shop.Customer/t
        Customer[] h = new Customer[2];   //> Customer=Shop.Customer/t Customer=Shop.Customer/t
        Point? i = null;   //> Point=Shop.Point/t
        foreach (Order j in orders) { }   //> Order=Shop.Order/t
        (Order k, Customer l) = (a, new Customer());   //> Order=Shop.Order/t Customer=Shop.Customer/t Customer=Shop.Customer/t
        Func<Order, Money> m = (Order x) => new Money(x.Total);   //> Order=Shop.Order/t Money=Shop.Money/t Order=Shop.Order/t Money=Shop.Money/t
        Money Local(Customer x) => Money.Zero;   //> Money=Shop.Money/t Customer=Shop.Customer/t Money=Shop.Money/r
        var n = Enumerable.Empty<Order>();   //> Order=Shop.Order/t
        var p = new Order.Line();   //> Order=Shop.Order/t Line=Shop.Order.Line/t
        var q = new global::Shop.Order();   //> Shop=- Order=Shop.Order/t
        var r = new Shop.Order();   //> Shop=- Order=Shop.Order/t
        try { } catch (OrderException) { }   //> OrderException=Shop.OrderException/t
        try { } catch (OrderException s) when (s.Message != "") { }   //> OrderException=Shop.OrderException/t
        var u = o switch { Order => 1, Customer { Name: "" } => 2, _ => 3 };   //> Order=Shop.Order/r Customer=Shop.Customer/t
        var v = new Repo();   //> Repo=Shop.Repo/t
        var w = new Repo<Order>();   //> Repo=Shop.Repo/t Order=Shop.Order/t
        IRepo<Point> y = w as IRepo<Point> ?? throw new OrderException();   //> IRepo=Shop.IRepo/t Point=Shop.Point/t IRepo=Shop.IRepo/t Point=Shop.Point/t OrderException=Shop.OrderException/t
        return Order.Max;   //> Order=Shop.Order/r
    }

    public void Receivers()
    {
        var a = Order.Create();   //> Order=Shop.Order/r
        var b = Order.Max + Order.Empty.Total;   //> Order=Shop.Order/r Order=Shop.Order/r
        var c = Order.Line.Make();   //> Order=Shop.Order/r Line=Shop.Order.Line/r
        Util.Helper.Run();   //> Util=Shop.Util/r Helper=Shop.Util.Helper/r
        var d = Util.Version.Length;   //> Util=Shop.Util/r
        var e = Shop.Order.Create();   //> Shop=- Order=Shop.Order/r
        var f = global::Shop.Status.Open;   //> Shop=- Status=Shop.Status/r
        var g = nameof(Customer);   //> Customer=Shop.Customer/r
        var h = nameof(Order.Create);   //> Order=Shop.Order/r
        var i = Repo<int>.Make();   //> Repo=Shop.Repo/r
        var j = Money.Zero with { Amount = 1 };   //> Money=Shop.Money/r
        switch (Status.Open)   //> Status=Shop.Status/r
        {
            case Status.Closed: break;   //> Status=Shop.Status/r
        }
        var k = Status.Open is Status.Closed;   //> Status=Shop.Status/r Status=Shop.Status/r
        var l = "😀" + Order.Max;   //> Order=Shop.Order/r
    }
}
