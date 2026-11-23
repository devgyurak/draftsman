namespace Shop.Pat
{
    public class Strings
    {
        public object A() => $"{{Order.Count}}";
        public object B() => $$"""{Order.Count} {{Money.Count}}""";
        public object C() => $@"{{Status.Count}} {Money.Count}";
        public object D() => "Order.Count";
        public object E() => $"{Money.Count:Order} {Money.Count,5}";
        public object F() => """
            Order.Count {Status.Count}
            """;
        public object G() => 'O' + @"Order.Count";
    }
}
