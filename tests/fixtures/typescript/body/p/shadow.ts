import { Foo, Shape } from "./foo";
import { Shop } from "./shop";

// a namespace is a scope inside the module: its own types and aliases come before the
// file's imports of the same name
export namespace Local {
  class Foo {                                 //> Foo=-
    static make(): number {
      return 2;
    }
  }
  import Shape = Shop.Item;                   //> Shape=- Shop=- Item=-
  export class User {
    use(): unknown {
      const s: Shape | null = null;           //> Shape=p/shop.Shop.Item/t
      return [s, Foo.make(), new Foo()];      //> Foo=p/shadow.Local.Foo/r Foo=p/shadow.Local.Foo/r
    }
  }
}

// outside it, the imports
export class Outside {
  use(): unknown {
    const s: Shape | null = null;             //> Shape=p/foo.Shape/t
    return [s, Foo.create()];                 //> Foo=p/foo.Foo/r
  }
}
