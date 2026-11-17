using System;
using System.Threading.Tasks;
using Shop.Orders;
using Stripe;

namespace Shop.Payments
{
    public interface IPaymentGateway
    {
        Task<Receipt> ChargeAsync(Order order);
    }

    public class StripeGateway : IPaymentGateway, IDisposable
    {
        private StripeClient client;
        private Receipt.Money fee;

        public Task<Receipt> ChargeAsync(Order order) => Task.FromResult<Receipt>(null);
        public void Dispose() { }
    }

    public class Receipt
    {
        public string Id { get; init; }
        public Money Amount { get; init; }

        public record Money(long Cents, string Currency);
    }
}
