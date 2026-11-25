using Lib;

// #4: `Repo<int>` takes one type argument: Lib.Repo<T>, not Shop.Repo
namespace Shop.Sub2
{
    public class XR
    {
        public Repo<int> R;
        public Repo<int> Get() => null;
        public Repo Plain;
        public object Make() => new Repo<int>();
    }

    public class XR2 : Repo<string> { }
}
