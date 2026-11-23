using System;

namespace Shop;

// saved with a byte order mark and CRLF line ends
public class Crlf
{
    public object M() => new Order();   //> Order=Shop.Order/t
    public string N() => "😀" + Customer.Guest.Name;   //> Customer=Shop.Customer/r
}
