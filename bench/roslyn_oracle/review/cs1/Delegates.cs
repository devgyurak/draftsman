namespace Shop.Del
{
    public delegate void Handler();
    public class Uses
    {
        public delegate void Task();
        public object M() { Handler h = null; return h; }
        public object N() { Task t = null; return t; }
        public object P() => typeof(Handler);
    }
}
