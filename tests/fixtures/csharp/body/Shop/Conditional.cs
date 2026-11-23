#if NET11_0_OR_GREATER
using Lib;
#else
using Lib2;
#endif

namespace Shop.Conditional;

// a name through a using one build leaves out, a field only the #else branch declares:
// each build resolves it differently
public class Uses
{
    public object M() => new Invoice();   //> Invoice=split/t
}

public class Holder
{
    public int Guest = 1;
}

public class Fields
{
#if NET11_0_OR_GREATER
    public int Spare;
#else
    public Holder Customer = null!;
#endif
    public object M() => Customer.Guest;   //> Customer=split/r
}
