using SO = Lib.Order;
namespace Shop.Rev.Target.Scoped;
using SO2 = Lib.Order;

// an alias before `namespace X;` is looked up from the global namespace, one after it from
// X, where Shop.Rev.Target.Lib comes first
public class ScopedAlias
{
    public object A() => new SO();   //> SO=Lib.Order/t
    public object B() => SO.Count;   //> SO=Lib.Order/r
    public object C() => new SO2();   //> SO2=Shop.Rev.Target.Lib.Order/t
}
