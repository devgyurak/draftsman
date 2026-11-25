namespace A { public class Node {} public class Item {} public class T {} }
namespace B { public class Node {} }
namespace A
{
    public class Outer<X> { public class Inner<Y> {} }
    public class Base<X> {}
}
