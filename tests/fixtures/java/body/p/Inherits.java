package p;

import java.util.HashMap;

class Inherits extends HashMap<String, String> {
    Object named() {
        Entry e = null;                                     //> Entry=java.util.Map.Entry/t
        return e;
    }

    Thread anonymous() {
        return new Thread() {                               //> Thread=java.lang.Thread/t
            public void run() {
                State s = State.NEW;                        //> State=java.lang.Thread.State/t State=java.lang.Thread.State/r
            }
        };
    }
}
