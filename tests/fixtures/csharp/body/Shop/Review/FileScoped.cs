namespace Shop.Rev.Web;
using System.Threading.Tasks;

// a using after a file-scoped namespace is that namespace's: before Shop.Rev's Task
public class Scoped
{
    public object A() { Task t = null!; return t; }   //> Task=System.Threading.Tasks.Task/t
    public object B() => Task.CompletedTask;   //> Task=System.Threading.Tasks.Task/r
}
