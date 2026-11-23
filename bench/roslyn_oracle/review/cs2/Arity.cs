namespace Shop.Ar
{
    public class Repo { public static int Count = 0; }
    public class Uses
    {
        public object A() => new Repo();
        public object B() => new Repo<int>();
        public object C() => Repo.Count;
        public object D() => Repo<int>.Count;
    }
}
