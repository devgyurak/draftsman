using Lib;
#if !NET11_0_OR_GREATER
using Ticket = Lib2.Ticket;
#endif

namespace Shop.Conditional;

// an alias only one build declares comes before the using
public class Aliased
{
    public object M() => new Ticket();   //> Ticket=split/t
}
