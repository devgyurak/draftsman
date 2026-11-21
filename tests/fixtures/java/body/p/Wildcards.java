package p;

import java.util.*;
import java.util.concurrent.*;

// supertypes through wildcard imports pass on their nested types too: Map.Entry and
// Future.State, not the package's own Entry and State
abstract class Wildcards extends AbstractMap<String, String> implements Future<String> {
    Object named() {
        Entry<String, String> e = null;                     //> Entry=java.util.Map.Entry/t String=java.lang.String/t String=java.lang.String/t
        State s = null;                                     //> State=java.util.concurrent.Future.State/t
        return new HashMap<String, String>() {              //> HashMap=java.util.HashMap/t String=java.lang.String/t String=java.lang.String/t
            Object anonymous() {                            //> Object=java.lang.Object/t
                Entry<String, String> a = null;             //> Entry=java.util.Map.Entry/t String=java.lang.String/t String=java.lang.String/t
                return a;
            }
        };
    }
}

abstract class WildcardSub extends Wildcards {
    Object inherited() {
        Entry<String, String> e = null;                     //> Entry=java.util.Map.Entry/t String=java.lang.String/t String=java.lang.String/t
        return e;
    }
}
