using System;

namespace Shop.Orders
{
    public partial class Order
    {
        public void AddLine(OrderLine line)
        {
            Action a = () => lines.Add(line);
            a();
        }
    }
}
