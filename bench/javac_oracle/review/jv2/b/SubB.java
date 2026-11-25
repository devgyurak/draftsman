package b;
public class SubB extends a.Base {
    Pkg p;
    Prot q;
    Pub r;
    Priv s;
    Object m() { Pkg x = new Pkg(); Prot y = null; Priv z = new Priv(); return x; }
    class In {
        Pkg p2;
        Priv s2;
        Pub r2;
    }
}
