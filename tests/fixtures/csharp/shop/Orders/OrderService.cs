using System.Collections.Generic;
using System.Threading.Tasks;
using Shop.Payments;
using Microsoft.EntityFrameworkCore;

namespace Shop.Orders
{
    public interface IOrderRepository : IRepository<Order>
    {
        IEnumerable<Order> FindByCustomer(Customer customer);
    }

    public class OrderService
    {
        private readonly IOrderRepository repository;
        private readonly IPaymentGateway gateway;
        internal static OrderService Instance;

        public OrderService(IOrderRepository repository, IPaymentGateway gateway)
        {
            this.repository = repository;
            this.gateway = gateway;
        }

        public Order Place(Customer customer, List<OrderLine> lines) => null;

        public Task<Receipt> PayAsync(Order order) => gateway.ChargeAsync(order);

        public T Reload<T>(T order) where T : Order => order;
    }
}
