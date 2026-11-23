namespace Shop.Rev.Parts
{
    // PartB.cs declares a field Order in the #else branch only: net10.0 reads the field
    public partial class Split
    {
        public object A() => nameof(Order);   //> Order=split/r
    }
}
