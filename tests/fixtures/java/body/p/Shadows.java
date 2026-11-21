package p;

class Shadows extends Base implements Consts {
    String Entry = "e";

    void param(String Pet) {
        Pet.length();                                       //> Pet=var/r
    }

    void field() {
        Entry.length();                                     //> Entry=var/r
        Runnable r = () -> Entry.length();                  //> Runnable=java.lang.Runnable/t Entry=var/r
        Entry x = null;                                     //> Entry=p.Entry/t
    }

    void inherited() {
        Util.length();                                      //> Util=var/r
        Owner.length();                                     //> Owner=var/r
    }

    class Inner {
        void outerSuper() {
            Util.length();                                  //> Util=var/r
        }
    }

    <Owner> Object typeParam(Object o) {                    //> Owner=-/t
        return (Owner) o;                                   //> Owner=tparam/t
    }

    Object localClass() {
        class Util {                                        //> Util=-/t
        }
        return new Util();                                  //> Util=local/t
    }
}
