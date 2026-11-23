using Random = Shop.Random;
namespace System.Mine2
{
    public class AliasOutside
    {
        public object A() => new Random();
        public object B() => Random.Shared;
    }
}
namespace Plain
{
    public class AliasPlain
    {
        public object A() => new Random();
        public object B() => Random.Count;
    }
}
