using Shop.Rev.Around;

namespace Shop.Rev.Around
{
    // a type named as a System one, which the using above brings into the namespaces below
    public class Random
    {
        public static int Count;
    }
}

namespace Environment
{
    public class SpecialFolder
    {
    }
}

// a namespace outside the sources around the code: its types come before the file's
// usings, and so do those of each namespace it is in
namespace System.Mine
{
    public class Dice
    {
        public object A() => Random.Shared;   //> Random=System.Random/r
        public object B() => new Random();   //> Random=System.Random/t
        // System's Environment is nearer than the global namespace Environment
        public object C() => typeof(Environment.SpecialFolder);   //> Environment=System.Environment/t SpecialFolder=System.Environment.SpecialFolder/t
    }
}

namespace System.Collections.Mine
{
    public class Deck
    {
        public object A() => new Random();   //> Random=System.Random/t
    }
}
