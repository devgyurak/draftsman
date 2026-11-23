namespace Shop.Use
{
    class A
    {
        void M()
        {
            var a = new Outer.Mid.Leaf();
            var b = Outer.Mid.Leaf.N;
            var c = typeof(Shop.Outer.Mid.Leaf);
            var d = new Gen<int>.Inner();
            var e = Gen<int>.Inner.N;
            var f = new Gen.Inner();
            var g = typeof(Gen<>.Inner);
            var h = Models.Order.Count;
            var i = new Models.Order();
        }
    }
}
