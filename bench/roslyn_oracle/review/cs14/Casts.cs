namespace Shop.Pat
{
    public class Casts
    {
        public int[] Money = new int[1];
        public int Order = 1;
        public object A() => (Money)[0];
        public object B() => (Order) + 1;
        public object C() => (Order) * 2;
        public object D() => (Order) & 1;
        public object E() => (Order) - 1;
        public object F() => (Order) | 1;
        public object G() => (Order) is int;
        public object H() => (Order) switch { 1 => 2, _ => 3 };
        public object I() => (Order) == 1;
        public object J() => (Order) < 1;
        public object K() => (Order) % 2;
        public object L() => (Order) / 2;
        public object M() => (Order) ^ 1;
        public object N() => (Order) >> 1;
        public object Q() => (Order).GetHashCode();
        public object R() => (Order)++;
        public object S() => Status.Count;
    }
}
