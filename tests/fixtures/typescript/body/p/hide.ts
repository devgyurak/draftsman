import { Foo, Kind } from "./foo";
import { Starred } from "./bar";

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

// a namespace's own variables and functions are values in the bodies of its classes,
// and in those of the namespaces inside it
export namespace Block {
  const Foo = { create: () => 1 };            //> Foo=-
  export const Starred = { n: 1 };            //> Starred=-
  function Kind(): number {                   //> Kind=-
    return 1;
  }
  export class User {
    use(): number {
      const k: Kind | null = null;            //> Kind=p/foo.Kind/t
      void [k, Kind()];                       //> Kind=var/r
      return Foo.create();                    //> Foo=var/r
    }
  }
  export namespace Inner {
    export class Deeper {
      use(): number {
        return Foo.create() + Kind();         //> Foo=var/r Kind=var/r
      }
    }
  }
}

// an exported one in every block of the namespace (`Block.Nested` is in Block)
export namespace Block.Nested {
  export class Far {
    use(): number {
      return Starred.n;                       //> Starred=var/r
    }
  }
}

// and not in a class outside the namespace
export class Outside {
  use(): number {
    return new Foo() && new Starred() && Kind.A;   //> Foo=p/foo.Foo/r Starred=p/bar.Starred/r Kind=p/foo.Kind/r A=-
  }
}
