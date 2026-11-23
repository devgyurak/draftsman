using Lib;
namespace Shop.Files
{
    file class Local { public static int Count = 6; }
    // FileA's `file class Helper` is not seen here: Shop.Helper around
    public class InB
    {
        public object M() => new Helper();
        public object N() => Helper.Count;
        public object P() => Local.Count;
    }
}
