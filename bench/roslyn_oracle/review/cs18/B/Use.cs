using Lib2;

// #4: Core.Order of L is internal: lookup goes on to `using Lib2;`
namespace Core.Sub
{
    public class X
    {
        public Order O;
        public Order Get(Order o) => o;
        public Pub P;
        public object Make() => new Order();
    }

    public class X2 : Order { }
}
