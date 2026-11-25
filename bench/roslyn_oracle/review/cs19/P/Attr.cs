using System;

namespace Shop
{
    public class Base6
    {
        public string Order => "";
        public Kind Kind => Kind.A;
    }

    [Tag(nameof(Order))]
    public class OnClass : Base6
    {
        [Tag(typeof(Order))]
        public void M() { }

        [Tag(Kind.A)]
        public void N() { }

        [Tag(nameof(Order))]
        public void O2() { }
    }

    public class WithNested
    {
        public class Order { }

        [Tag(nameof(Order))]
        public void M() { }

        [Tag(typeof(Order))]
        public void N() { }
    }
}
