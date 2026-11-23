namespace Shop.Rev.Del
{
    // a delegate is a type: it hides one of its name further out
    public delegate void Handler();
    public class Uses
    {
        public delegate void Task();
        public object M() { Handler h = null!; return h; }   //> Handler=Shop.Rev.Del.Handler/t
        public object N() { Task t = null!; return t; }   //> Task=Shop.Rev.Del.Uses.Task/t
        public object P() => typeof(Handler);   //> Handler=Shop.Rev.Del.Handler/t
    }
}
