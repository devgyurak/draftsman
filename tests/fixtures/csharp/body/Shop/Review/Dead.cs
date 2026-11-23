namespace Shop.Rev.Dead
{
    // `#if false` is compiled by no build, its #else by every one
    public class Never
    {
#if false
        public object A() => new Order();   //> Order=-
        public int Status = 0;
#endif
        public object B() => Status.Open;   //> Status=Shop.Status/r
#if false
        public object C() => new Order();   //> Order=-
#else
        public object D() => new Order();   //> Order=Shop.Order/t
#endif
#if !true
        public object E() => new Order();   //> Order=-
#endif
#if (false)
        public object F() => new Order();   //> Order=-
#endif
#if false || false
        public object G() => new Order();   //> Order=-
#endif
#if true
        public class Always
        {
        }
#else
        public int Order = 0;
#endif
        public object H() => new Always();   //> Always=Shop.Rev.Dead.Never.Always/t
        public object I() => new Order();   //> Order=Shop.Order/t
    }
}
