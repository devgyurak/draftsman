package p;

import static java.lang.Thread.State;

class ExternalStatic {
    void use() {
        Object s = State.NEW;                               //> Object=java.lang.Object/t State=java.lang.Thread.State/r
    }
}
