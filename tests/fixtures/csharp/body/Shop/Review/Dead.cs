namespace Shop.Rev.Dead
{
    // `#if false` is compiled by no build
    public class Never
    {
#if false
        public object A() => new Order();   //> Order=-
#endif
        public object B() => Status.Open;   //> Status=Shop.Status/r
    }
}
