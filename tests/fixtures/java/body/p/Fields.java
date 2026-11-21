package p;

import static java.util.concurrent.TimeUnit.*;
import static p.Both.Twin;

import java.util.logging.*;

// a variable of a type's name wins in receiver position: fields of every kind, from
// wherever they come into scope
class Fields {
    long staticStar() {
        return SECONDS.toMillis(1);                         //> SECONDS=var/r
    }

    void staticSingle() {
        Twin.toString();                                    //> Twin=var/r
        Twin t = null;                                      //> Twin=p.Both.Twin/t
        Both.Twin.toString();                               //> Both=p.Both/r Twin=var/r
    }
}

class Levels extends Level {
    Levels() {
        super("levels", 1);
    }

    String inheritedThroughWildcard() {
        return SEVERE.getName();                            //> SEVERE=var/r
    }
}

class Anonymous {
    Object project() {
        return new Base() {                                 //> Base=p.Base/t
            int field() {
                return Util.length();                       //> Util=var/r
            }
        };
    }

    Object jdk() {
        return new Level("anonymous", 2) {                  //> Level=java.util.logging.Level/t
            String field() {                                //> String=java.lang.String/t
                return SEVERE.getName();                    //> SEVERE=var/r
            }
        };
    }
}

class Enclosing {
    static Object Owner = null;

    static class Nested {
        String outerField() {
            return Owner.toString();                        //> Owner=var/r
        }
    }
}

enum Modes {
    Owner;

    String constant() {
        return Owner.name();                                //> Owner=var/r
    }
}

record Pair(Object Owner) {
    Pair {
        Owner.hashCode();                                   //> Owner=var/r
    }

    String component() {
        return Owner.toString();                            //> Owner=var/r
    }
}

class Both {
    static Object Twin = "";

    static class Twin {
    }
}

// the traps: project types named like the fields above
class SECONDS {
    static long toMillis(long n) {
        return n;
    }
}

class SEVERE {
    static String getName() {
        return "";
    }
}
