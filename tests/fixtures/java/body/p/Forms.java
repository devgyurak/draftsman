package p;

import java.util.ArrayList;
import java.util.List;
import java.util.function.Function;
import p.a.*;

class Forms {
    static Owner DEFAULT = Owner.create();                  //> Owner=-/t Owner=p.Owner/r

    static {
        Util.make();                                        //> Util=p.Util/r
    }

    Object forms(Object o) {
        Owner a = new Owner();                              //> Owner=p.Owner/t Owner=p.Owner/t
        Object b = (Owner) o;                               //> Owner=p.Owner/t
        boolean c = o instanceof Owner;                     //> Owner=p.Owner/t
        try {
            a.getName();
        } catch (ShopException e) {                         //> ShopException=p.ShopException/t
        }
        Class<?> d = Owner.class;                           //> Owner=p.Owner/t
        List<Owner> f = new ArrayList<Owner>();             //> List=java.util.List/t Owner=p.Owner/t ArrayList=java.util.ArrayList/t Owner=p.Owner/t
        String g = Util.VALUE;                              //> Util=p.Util/r
        Function<Owner, String> h = Owner::getName;         //> Function=java.util.function.Function/t Owner=p.Owner/t Owner=p.Owner/r
        p.Util.make();                                      //> Util=p.Util/r
        Util.Helper.run();                                  //> Util=p.Util/r Helper=p.Util.Helper/r
        new Util.Helper();                                  //> Util=p.Util/t Helper=p.Util.Helper/t
        Pet i = new Pet();                                  //> Pet=p.a.Pet/t Pet=p.a.Pet/t
        Owner Owner = new Owner();                          //> Owner=p.Owner/t Owner=-/t Owner=p.Owner/t
        Owner.getName();                                    //> Owner=var/r
        return Owner;                                       //> Owner=-/t
    }
}
