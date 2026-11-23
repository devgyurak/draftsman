namespace A.B
{
    using O = Lib.Order;
    public class BlockAlias
    {
        public object M() => new O();
        public object N() => O.Count;
    }
}
