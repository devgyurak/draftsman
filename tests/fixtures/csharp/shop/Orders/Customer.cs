using System.Collections.Generic;
using Shop.Common;

namespace Shop.Orders;

public class Customer : BaseEntity
{
    public string Name { get; set; }
    private readonly List<Order> orders = new();
    public Address HomeAddress { get; set; }
    private IListener? listener;   // inherited member type: BaseEntity.IListener

    public class Address
    {
        public string Street;
    }

    public override bool IsNew() => Id == 0;
}
