package p;

enum Kind {
    A(Util.VALUE),                                          //> Util=p.Util/r
    B(Util.VALUE) {                                         //> Util=p.Util/r
    };

    Kind(String s) {
    }
}
