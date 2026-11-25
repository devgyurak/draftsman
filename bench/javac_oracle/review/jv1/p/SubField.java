package p;
// bodies of a subclass: Base's protected Deep and public Item are inherited (beside p.Deep, p.Item)
public class SubField extends Mid {
    Object m() { Deep d = new Deep(); Item i = new Item(); return d; }
}
