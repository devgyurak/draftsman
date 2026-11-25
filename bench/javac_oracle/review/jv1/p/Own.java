package p;
// #49: a class sees its own private nested type, and so do the types nested in it
public class Own {
    private static class Hidden {}
    Hidden a;
    static class Nest {
        Hidden b;
        Object m() { return new Hidden(); }
    }
}
