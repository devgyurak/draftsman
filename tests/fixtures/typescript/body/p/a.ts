import { Foo, Shape, Kind, Alias, Token, decorate } from "./foo";
import * as ns from "./foo";
import { Bar as Renamed } from "./bar";
import { Baz, Starred } from "./barrel";

function Helper(): number {
  return 1;
}

function register(...types: unknown[]): void {}

@decorate(Foo)
export class A {
  private readonly made = new Foo();          //> Foo=p/foo.Foo/r
  // a field is no name in a body: `Kind` below is the enum
  Kind = 0;

  static {
    Foo.create();                             //> Foo=p/foo.Foo/r
  }

  get shape(): Shape | null {
    const s: Shape | null = null;             //> Shape=p/foo.Shape/t
    return s;
  }

  types(o: unknown): void {
    const f = new Foo();                      //> Foo=p/foo.Foo/r
    const g: Foo = Foo.create();              //> Foo=p/foo.Foo/t Foo=p/foo.Foo/r
    const s = o as Shape;                     //> Shape=p/foo.Shape/t
    const q = { area: () => 1 } satisfies Shape;   //> Shape=p/foo.Shape/t
    const k = Kind.A;                         //> Kind=p/foo.Kind/r A=-
    const x = Foo.X;                          //> Foo=p/foo.Foo/r X=-
    const i = new Foo.Inner();                //> Foo=p/foo.Foo/r Inner=p/foo.Foo.Inner/r
    const j: Foo.Inner = i;                   //> Foo=p/foo.Foo/t Inner=p/foo.Foo.Inner/t
    const n = new ns.Foo();                   //> Foo=p/foo.Foo/r
    const t: ns.Shape | null = null;          //> Shape=p/foo.Shape/t
    const r = new Renamed();                  //> Renamed=p/bar.Bar/r
    const b = new Baz();                      //> Baz=p/baz.Baz/r
    const st: Starred = new Starred();        //> Starred=p/bar.Starred/t Starred=p/bar.Starred/r
    const al: Alias = f;                      //> Alias=alias/t
    const m = new Map<string, Foo>();         //> Map=Map/r Foo=p/foo.Foo/t
    const c: typeof Foo = Foo;                //> Foo=p/foo.Foo/r Foo=p/foo.Foo/r
    const obj = { Foo, kind: Kind.B };        //> Foo=p/foo.Foo/r Kind=p/foo.Kind/r B=-
    register(Foo, [Kind]);                    //> Foo=p/foo.Foo/r Kind=p/foo.Kind/r
    if (o instanceof Foo) {                   //> Foo=p/foo.Foo/r
      void [g, s, q, k, x, j, n, t, r, b, st, al, m, c, obj];
    }
  }

  values(): void {
    const tok = Token;                        //> Token=var/r
    const tt: Token = { t: tok };             //> Token=p/foo.Token/t
    const h = Helper();                       //> Helper=var/r
    void [tt, h];
  }

  parameter(Foo: number): void {
    const v = Foo + 1;                        //> Foo=var/r
    const w: Foo | null = null;               //> Foo=p/foo.Foo/t
    void [v, w];
  }

  locals(items: unknown[]): void {
    const Kind = { A: 1 };
    const v = Kind.A;                         //> Kind=var/r A=-
    class Local implements Shape {            //> Local=- Shape=p/foo.Shape/t
      area(): number {
        return v;
      }
    }
    class Derived extends Foo {}              //> Derived=- Foo=p/foo.Foo/r
    const l: Local = new Local();             //> Local=local/t Local=local/r
    const d = new Derived();                  //> Derived=local/r
    for (const Baz of items) {                //> Baz=-
      void Baz;                               //> Baz=var/r
    }
    try {
      void items.map((Renamed) => Renamed);   //> Renamed=- Renamed=var/r
    } catch (Starred) {                       //> Starred=-
      void Starred;                           //> Starred=var/r
    }
    function Inner(): void {}
    Inner();                                  //> Inner=var/r
    {
      const { Foo } = { Foo: 1 };             //> Foo=- Foo=-
      void [l, d, Foo];                       //> Foo=var/r
    }
  }

  generic<T>(x: T): T {
    const y: T = x;                           //> T=tparam/t
    return y;
  }
}

export enum Level {
  Low = Kind.A,                               //> Low=- Kind=p/foo.Kind/r A=-
}
