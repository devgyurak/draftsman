using Shop;

// #2: no alias here: `Order` is Shop.Order through `using Shop;`
public class Y
{
    public Order O;
    public Order Get(Order o) => o;
    public object Make() => new Order();
}

public class YBase : Order { }
