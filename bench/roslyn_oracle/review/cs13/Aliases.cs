namespace A
{
    namespace B
    {
        using NO = Lib.Order;
        using GL = G.Lib<int>;
        public class Nested
        {
            public object A1() => new NO();
            public object A2() => NO.Count;
            public object A3() => new GO();
            public object A4() => GO.Count;
            public object A5() => new CO();
            public object A6() => CO.Count;
            public object A7() => new GL.Order();
            public object A8() => GL.Order.Count;
        }
    }
}
