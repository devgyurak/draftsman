namespace Lib
{
    public class Order { }
    public class Money { }
    public class Pair<A, B> { }
}

namespace Shop
{
    public class Order { }
    public class Pair<T> { }
    public class ShopOptions { }
    public class ServiceDescriptor { }
    public enum Kind { A, B }

    public class TagAttribute : System.Attribute
    {
        public TagAttribute(System.Type t) { }
        public TagAttribute(Kind k) { }
        public TagAttribute(string s) { }
    }
}
