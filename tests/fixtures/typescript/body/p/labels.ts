import { Foo, Kind } from "./foo";
import { Bar } from "./bar";

export class Labels {
  // a label in a type is no name: a tuple member's, an index signature's parameter
  labels(): void {
    const a: [Foo: string, Bar?: number] | null = null;   //> Foo=- Bar=-
    const b: { [Kind: string]: number } | null = null;    //> Kind=-
    void [a, b];
  }

  // an import type names the module's type
  imported(): void {
    const g: import("./bar").Bar | null = null;           //> Bar=p/bar.Bar/t
    const h: typeof import("./bar").Bar | null = null;    //> Bar=p/bar.Bar/r
    void [g, h, new Bar()];                               //> Bar=p/bar.Bar/r
  }
}
