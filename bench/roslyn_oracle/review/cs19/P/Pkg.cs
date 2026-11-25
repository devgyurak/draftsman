using Shop;

namespace Microsoft.Extensions.DependencyInjection
{
    public static class ShopExtensions
    {
        public static IServiceCollection AddShop(this IServiceCollection s, ShopOptions o) => s;
        public static ServiceDescriptor Describe(ServiceDescriptor d) => d;
    }

    public class Holder5
    {
        public ShopOptions Options;
        public ServiceDescriptor D;
    }
}
