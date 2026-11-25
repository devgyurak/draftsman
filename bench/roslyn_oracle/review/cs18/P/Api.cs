using Order = Lib.Order;

// #2: an alias of a file without a namespace is this file's only
public class Api
{
    public Order O;
    public Order Get(Order o) => o;
    public object Make() => new Order();
}

public class ApiBase : Order { }
