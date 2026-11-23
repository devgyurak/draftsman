using Shop;
using Lib;
namespace Other.Cs
{
    // aliases the build declares (<Using Alias>, a global using alias in another file) come
    // before the usings' types
    public class Uses
    {
        public object A() => new Ord();
        public object B() => Ord.Count;
        public object C() => Receipt.Count;
    }
}
