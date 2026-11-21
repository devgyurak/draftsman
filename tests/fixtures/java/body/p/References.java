package p;

import java.util.List;
import java.util.function.Function;
import java.util.function.IntFunction;
import java.util.function.Supplier;

// method references: the qualifier is a receiver where a variable could stand (`Owner::new`),
// a type where only one can (`Owner[]::new`, `List<Owner>::size`, `Named.super::name`)
class References implements Named {
    void m() {
        Supplier<Owner> a = Owner::new;                     //> Supplier=java.util.function.Supplier/t Owner=p.Owner/t Owner=p.Owner/r
        IntFunction<Owner[]> b = Owner[]::new;              //> IntFunction=java.util.function.IntFunction/t Owner=p.Owner/t Owner=p.Owner/t
        Function<List<Owner>, Integer> c = List<Owner>::size; //> Function=java.util.function.Function/t List=java.util.List/t Owner=p.Owner/t Integer=java.lang.Integer/t List=java.util.List/t Owner=p.Owner/t
        Supplier<String> d = Named.super::name;             //> Supplier=java.util.function.Supplier/t String=java.lang.String/t Named=p.Named/t
        Function<Owner, String> e = p.Owner::getName;       //> Function=java.util.function.Function/t Owner=p.Owner/t String=java.lang.String/t Owner=p.Owner/r
    }
}
