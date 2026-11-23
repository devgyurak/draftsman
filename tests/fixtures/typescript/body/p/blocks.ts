import { Bar, Starred } from "./bar";

// a namespace's member that is not exported is seen in its own block only, an exported
// one in every block of the namespace
export namespace Split {
  class Bar {                                 //> Bar=-
    static make(): number {
      return 2;
    }
  }
  export class Starred {}                     //> Starred=-
  // exported from a namespace this block does not export: another block's Inner is
  // another namespace
  namespace Inner {
    export class Bar {}                       //> Bar=-
  }
  export class Near {
    use(): unknown {
      const b: Bar | null = null;             //> Bar=p/blocks.Split.Bar/t
      return [b, Bar.make(), new Starred()];  //> Bar=p/blocks.Split.Bar/r Starred=p/blocks.Split.Starred/r
    }
  }
}

export namespace Split {
  namespace Inner {
    export class Deep {
      use(): unknown {
        return new Bar();                     //> Bar=p/bar.Bar/r
      }
    }
  }
  export class Far {
    use(): unknown {
      const b: Bar | null = null;             //> Bar=p/bar.Bar/t
      return [b, new Bar(), new Starred()];   //> Bar=p/bar.Bar/r Starred=p/blocks.Split.Starred/r
    }
  }
}
