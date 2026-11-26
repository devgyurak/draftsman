package p;
// #28: annotations on enum constants are the enum's
public enum Provider {
    JDK,
    @Unstable OPENSSL,
    @Other(Item.class) BORING { void f() {} }
}
