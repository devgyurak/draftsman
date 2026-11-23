using Lib2;
namespace Plain.Al
{
    using O3 = Order;
    public class OuterUsing
    {
        public object M() => new O3();
        public object N() => O3.Count;
    }
}
