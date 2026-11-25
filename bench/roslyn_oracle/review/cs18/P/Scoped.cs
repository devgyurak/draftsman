using Order = Lib.Order;

namespace Shop.Sub;

// #3: an alias of the compilation unit comes after the namespaces around the code
public class XS
{
    public Order O;
    public Order Get(Order o) => o;
    public object Make() => new Order();
}

public class XS2 : Order { }
