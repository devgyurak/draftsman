package p;

class Outer {
    class Inner {
    }

    class Only {
    }
}

// `o.new Inner()` names a member of o's type, Outer.Inner, not the package's Inner
class Qualified {
    Object make() {
        Outer o = new Outer();                              //> Outer=p.Outer/t Outer=p.Outer/t
        Object a = o.new Inner();                           //> Object=java.lang.Object/t Inner=p.Outer.Inner/t
        Object b = new Outer().new Inner();                 //> Object=java.lang.Object/t Outer=p.Outer/t Inner=p.Outer.Inner/t
        return o.new Only();                                //> Only=p.Outer.Only/t
    }
}

class QualifiedSub extends Outer {
    Object make(Outer o) {
        return o.new Inner();                               //> Inner=p.Outer.Inner/t
    }
}
