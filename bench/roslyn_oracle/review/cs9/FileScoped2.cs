using Shop;
namespace Microsoft.Extensions.Hosting;
public static class MyExt
{
    public static object A() => typeof(Host);
    public static object B() => Order.Count;
    public static object C() => Host.CreateDefaultBuilder();
}
