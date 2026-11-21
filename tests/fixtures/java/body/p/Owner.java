package p;

public class Owner {
    public static Owner create() {
        return new Owner();                                 //> Owner=p.Owner/t
    }

    public String getName() {
        return "o";
    }
}
