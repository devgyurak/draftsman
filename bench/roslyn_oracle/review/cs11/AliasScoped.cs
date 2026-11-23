using O1 = Lib.Order;
namespace A.C;
using O2 = Lib.Order;
public class ScopedAlias
{
    public object M() => new O1();
    public object N() => new O2();
    public object P() => O1.Count;
    public object Q() => O2.Count;
}
