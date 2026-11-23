namespace Shop.Blocks
{
    using System.Threading.Tasks;
    using static System.Console;

    // a using in the block comes before the namespaces around: System's Task, Console.Error
    public class Near
    {
        public object M() { Task t = null; return t; }
        public object N() => typeof(Task);
        public void P() => Error.WriteLine();
        public object Q() => Task.CompletedTask;
    }
}
namespace Shop.Kinds
{
    using static Shop.EntityKind;

    public class Kinds
    {
        public object M() => Order.ToString();
        public object N() => Customer.ToString();
    }
}
