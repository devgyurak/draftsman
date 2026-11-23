namespace Shop.Rev.Parts
{
#if NET11_0_OR_GREATER
    public partial class Split
    {
        public int Spare;
    }
#else
    public partial class Split
    {
        public int Order = 1;
    }
#endif
}
