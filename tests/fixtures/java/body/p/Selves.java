package p;

record Point(int x) {
    Point {
        Util.make();                                        //> Util=p.Util/r
    }
}

interface Named {
    default String name() {
        return "";
    }
}

class Selves implements Named {
    void m() {
        Util.<String>make();                                //> Util=p.Util/r
        Util /* a comment */ .make();                       //> Util=p.Util/r
    }

    public String name() {
        return Named.super.name();                          //> Named=p.Named/t
    }

    class Inner {
        Object n() {
            Selves.this.m();                                //> Selves=p.Selves/t
            return Selves.this;                             //> Selves=p.Selves/t
        }
    }
}
