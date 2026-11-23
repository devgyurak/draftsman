using Lib;
using static Shop.Util;

namespace Shop.Billing.Inner;

// the namespaces around come before the file's usings; `using static` brings in a class's
// static members and its nested types
public class Far
{
    public object M() => new Invoice();   //> Invoice=Shop.Billing.Invoice/t
    public object N() => new Order();   //> Order=Shop.Order/t
    public int K() => Lib.Order.Count;   //> Lib=- Order=Lib.Order/r
    public string V() => Version;
    public void H() => Helper.Run();   //> Helper=Shop.Util.Helper/r
}
