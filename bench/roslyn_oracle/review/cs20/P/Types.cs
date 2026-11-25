namespace Lib
{
    public class Order { }
    public class Money { }
    public class Box<T> { }
}

namespace Shop
{
    public class Cash { }
    public enum Kind { A, B }

    public class TagAttribute : System.Attribute
    {
        public TagAttribute(Kind k) { }
        public TagAttribute(string s) { }
    }
}

public class O { }
