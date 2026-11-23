import { Bar } from "./bar";

export class Labels {
  // an import type names the module's type
  imported(): void {
    const g: import("./bar").Bar | null = null;           //> Bar=p/bar.Bar/t
    const h: typeof import("./bar").Bar | null = null;    //> Bar=p/bar.Bar/r
    void [g, h, new Bar()];                               //> Bar=p/bar.Bar/r
  }
}
