namespace Shop.Rev.Outside
{
    // Exception.Data, a member of a base class outside the sources
    public class ShopException : System.Exception
    {
        public object A() => Data.Count;   //> Data=var/r
    }
}
