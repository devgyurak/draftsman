using System;

namespace Shop;

public class Order
{
    public const int Max = 10;
    public decimal Total;
    public static Order Create() => new Order();   //> Order=- Order=Shop.Order/t
    public static Order Empty { get; } = new Order();   //> Order=- Order=Shop.Order/t

    public class Line
    {
        public static Line Make() => new Line();   //> Line=- Line=Shop.Order.Line/t
    }
}

public class Customer
{
    public string Name = "";
    public static Customer Guest = new Customer();   //> Customer=- Customer=Shop.Customer/t
}

public class OrderException : Exception { }

public enum Status { Open, Closed, Last = Closed, Count = Status.Closed + 1 }   //> Status=- Status=Shop.Status/r

public static class Util
{
    public const string Version = "1";

    public static class Helper
    {
        public static void Run() { }
    }
}

public record Money(decimal Amount)
{
    public static Money Zero = new Money(0);   //> Money=- Money=Shop.Money/t
}

public struct Point
{
    public int X;
}

public interface IRepo<T>
{
    T Get();
}
