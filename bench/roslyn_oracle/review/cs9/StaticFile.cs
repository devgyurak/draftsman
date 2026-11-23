using static Shop.Holder;
namespace System.Mine3
{
    public class StaticOutside
    {
        public object A() => new Random();
        public object B() => Encoder.Count;
    }
}
namespace System.Text.Mine
{
    public class StaticText
    {
        public object A() => typeof(Encoder);
    }
}
