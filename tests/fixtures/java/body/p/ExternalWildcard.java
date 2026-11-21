package p;

import static java.util.Locale.*;

class ExternalWildcard {
    void use() {
        ENGLISH.getLanguage();                              //> ENGLISH=var/r
        Entry.create();                                     //> Entry=p.Entry/r
        Entry e = null;                                     //> Entry=p.Entry/t
    }
}
