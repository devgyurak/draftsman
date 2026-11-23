namespace Shop.Files
{
    file class Helper { public static int Count = 5; }
    file class Local { public static int Count = 5; }
    public class InA
    {
        public object M() => new Helper();
        public object N() => Local.Count;
    }
}
