namespace Lib
{
    public class Order { }
    public class Box<T> { }
    namespace Sub { public class Deep { } }
}

namespace Shop
{
    public class Order { }
    public class L { public class Order { } }
}
