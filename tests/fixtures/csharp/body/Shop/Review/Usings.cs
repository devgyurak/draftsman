namespace Shop.Rev.Blocks
{
    using System.Threading.Tasks;
    using static System.Console;

    // a using in the block comes before the namespaces around: System's Task, Console.Error
    public class Near
    {
        public object M() { Task t = null!; return t; }   //> Task=System.Threading.Tasks.Task/t
        public object N() => typeof(Task);   //> Task=System.Threading.Tasks.Task/t
        public void P() => Error.WriteLine();   //> Error=var/r
        public object Q() => Task.CompletedTask;   //> Task=System.Threading.Tasks.Task/r
    }
}
