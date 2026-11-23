namespace Shop.Rev.Files
{
    // a `file` type is seen in its file only; FileB.cs declares another Local
    file class Helper { public static int Count = 5; }
    file class Local { public static int Count = 5; }
    public class InA
    {
        public object M() => new Helper();   //> Helper=Shop.Rev.Files.Helper/t
        public object N() => Local.Count;   //> Local=Shop.Rev.Files.Local/r
    }
}
