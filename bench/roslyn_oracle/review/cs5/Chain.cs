using Shop;
namespace Microsoft.Extensions.Hosting
{
    // the namespace is .NET's too: its Host comes before the file's using
    public static class MyHostExtensions
    {
        public static object A() => Host.CreateDefaultBuilder();
        public static object B() => typeof(Host);
        public static object C() => Order.Count;
    }
}
namespace System.Mine
{
    public class InSystem
    {
        public object A() => Random.Shared;
        public object B() => new Random();
        public object C() => Order.Count;
    }
}
