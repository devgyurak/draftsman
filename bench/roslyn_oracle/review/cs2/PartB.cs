namespace Shop.Parts
{
    public partial class Whole
    {
        public int Money = 1;
    }
#if NET11_0_OR_GREATER
    public partial class Split
    {
        public int Spare;
    }
#else
    public partial class Split
    {
        public int Order = 1;
        public int Customer { get; set; }
    }
#endif
}
