using Shop;
namespace App
{
    public class D : Lib.Base
    {
        public object A() => new Money();
        public object B() => Hidden.Count;
        public object C() => Inner.Count;
        public object E() => Status.Count;
        public object F() => Shown.Count;
    }
    public class Io : IOException { public object A() => Data.Count; }
}
