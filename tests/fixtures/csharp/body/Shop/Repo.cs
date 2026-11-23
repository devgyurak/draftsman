namespace Shop;

// one id for two types: Repo and Repo<T> (ir.json writes no type arguments)
public class Repo
{
}

public class Repo<T> : IRepo<T>
{
    public T Get() => default!;
    public static Repo<T> Make() => new Repo<T>();   //> Repo=- Repo=Shop.Repo/t T=- T=tparam/t
}
