import { Foo, Kind } from "./foo";

// names declared outside the body that hide an imported class's value in it

export class Props {
  // a parameter property is a parameter in the constructor's body, `this.Foo` elsewhere
  constructor(private Foo: any, public readonly Kind?: any) {   //> Foo=- Kind=-
    Foo.create();                             //> Foo=var/r
    const k: Kind | null = Kind;              //> Kind=p/foo.Kind/t Kind=var/r
    void k;
  }

  other(): Foo {                              //> Foo=-
    return Foo.create();                      //> Foo=p/foo.Foo/r
  }
}

// an enum's members are values in its members' values
export enum Order {
  Foo = 1,                                    //> Foo=-
  Next = Foo + 1,                             //> Next=- Foo=var/r
  Last = Kind.B,                              //> Last=- Kind=p/foo.Kind/r B=-
}
