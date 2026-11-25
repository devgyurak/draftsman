using System;

// #35: `nameof(Order)` in an attribute is the class's member where it has one
namespace Shop
{
    public class Base2
    {
        public string Order => "";
    }

    public class Bodies : Base2
    {
        [Obsolete(nameof(Order))]
        public void M() { }
    }

    public class Plain2
    {
        [Obsolete(nameof(Order))]
        public void M() { }
    }
}
