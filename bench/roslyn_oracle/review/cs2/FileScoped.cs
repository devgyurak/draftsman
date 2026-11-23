namespace Shop.Web;
using System.Threading.Tasks;
using Util = System.Math;

// usings after a file-scoped namespace are that namespace's: before Shop's types
public class Scoped
{
    public object A() { Task t = null; return t; }
    public object B() => Task.CompletedTask;
    public object C() => Util.PI;
}
