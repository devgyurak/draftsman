package p;

import static p.Util.Helper;
import static p.Util.VALUE;

class StaticImports {
    void use() {
        Helper.run();                                       //> Helper=p.Util.Helper/r
        new Helper();                                       //> Helper=p.Util.Helper/t
        VALUE.length();                                     //> VALUE=var/r
    }
}
