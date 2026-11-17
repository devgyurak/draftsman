using System.Collections.Generic;
using Shop.Common;
using Shop.Promotions;

namespace Shop.Orders
{
    public enum Status { New, Paid, Shipped }

    public partial class Order : BaseEntity
    {
        public Customer Customer { get; set; }
        private IList<OrderLine> lines = new List<OrderLine>();
        public Status Status { get; set; }
        public Coupon? Coupon { get; set; }

        public override bool IsNew() => Status == Status.New;

        // a nested type naming a member type its enclosing class inherits
        public class Audit : IListener
        {
            public void Changed(BaseEntity entity) { }
        }
    }

    public record OrderLine(Product Product, int Quantity);

    public struct Product
    {
        public string Sku;
        public decimal Price;
    }
}
