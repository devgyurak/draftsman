namespace Shop.Rev.Files
{
    file class Local { public static int Count = 6; }
    // FileA.cs's Helper is not seen here: Shop.Rev's
    public class InB
    {
        public object M() => new Helper();   //> Helper=Shop.Rev.Helper/t
        public object N() => Local.Count;   //> Local=Shop.Rev.Files.Local/r
    }
}
