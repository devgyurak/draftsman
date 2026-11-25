package b;
public class Outer {
    static class NBase {
        private static class Priv {}
        static class Vis {}
    }
    static class NSub extends NBase {
        Priv a;
        Vis v;
        NBase.Priv q;
        Object m() { return new Priv(); }
    }
    private static class Mine {}
    Mine m;
    class In2 {
        Mine m2;
    }
}
