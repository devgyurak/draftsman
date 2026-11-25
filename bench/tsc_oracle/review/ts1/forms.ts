import { Options, Logger, Item, Key, Foo, T, U, K, Store, Color } from "./model";

// #29: aliases of types the parser read no name from
export type Both = | Options | Logger;
export type Joined = Options & Logger;
export type Obj = { item: Item; key?: Key };
export type Gen<T> = (x: T) => Item;
export type Cond<X> = X extends Array<infer U> ? U : Key;
export type Mapped<X> = { [K in keyof X]: Item };
export type Picked = Omit<Options, "a"> & { extra: Item };

// #32: supertypes that are aliases of several types, of an object type, of Omit
export interface I1 extends Joined {}
export interface I2 extends Obj {}
export interface I3 extends Picked {}
export class C1 implements Joined {
  a?: number;
  log(): void {}
}

// a value and a type of one name: `typeof value` is the value
export const value = { n: 1 };
export type value = Key;

export class A {
  logger: | "simple" | Logger = "simple";
  opts?: Options & { x?: number };
  map?: { item: Logger }[];
  props?: { Logger: string; Item: number; T: boolean };
  fn?: (Logger: string, item?: Item) => void;
  tup?: [Logger: string, n?: number];
  lit?: "Logger" | "Item";
  tpl?: `Logger-${number}`;
  tpl2?: `id-${Color}`;
  idx?: Store["Logger"];
  cond?: Options extends Logger ? Item : Key;
  both?: Both;
  gen?: Gen<Options>;
  c?: Cond<Item[]>;
  m?: Mapped<Options>;
  tv?: typeof value;
  ko?: keyof Logger;
  imp?: import("./other").Foo;
  own?: Foo;
  ctor?: new () => Item;
  gfn?: <T = Item>(x: T) => T;
  inferred?: Store extends { Item: infer U } ? U : never;
  keyed?: { [K in "a" | "b"]: Logger | K };
  index?: { [Key: string]: Item };
  method?: { run(x: Options): Logger; new (y: Key): Item };

  isLogger(x: unknown): x is Logger {
    return x instanceof Object;
  }
  check(x: unknown): asserts x is Options {}
  check2(x: unknown): asserts x {}
  self(): this is A {
    return true;
  }
  start({ a }: Options, [b]: [Item]): void {
    const k: Key = new Key();
  }
  later(opts?: { cb: (err?: Logger) => void }): Item | undefined {
    return undefined;
  }
}
