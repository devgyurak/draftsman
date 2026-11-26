import { Options, Logger, Item, Key, Entity, Leaf, Color, ns, Face, Base, R, F, Provider, Tree } from "./model";
import type * as M from "./model";

export class Shapes {
  a?: Promise<Array<Item | Key>>;
  b?: Map<string, Set<Item>>;
  c?: Record<string, Item>;
  d?: Partial<Options>;
  e?: ReadonlyArray<Item>;
  f?: readonly Key[];
  g?: (Item | Key)[];
  h?: [Item, ...Key[]];
  i?: [first: Item, ...rest: Key[]];
  j?: Item | null | undefined;
  k?: (this: Item, x: Key) => void;
  l?: typeof Item;
  m?: InstanceType<typeof Key>;
  n?: ns.Deep;
  o?: ns.inner.Leaf;
  p?: Color.Red;
  q?: M.Entity;
  r?: (() => Item) | Key;
  s?: () => Item | Key;
  t?: { "Item": string; 'Key': number; [Symbol.iterator](): Iterator<Leaf> };
  u?: {
    // Logger is only named in this comment
    a: Key; /* Item */
    b?: Options;
  };
  v?: "a|b" | "{Item}" | Leaf;
  w?: -1 | 0n | Key;
  x?: abstract new () => Item;
  y?: <F extends (x: Item) => void = (x: Key) => void>(f: F) => F;
  z?: Provider;
  tree?: Tree;
  [key: string]: unknown;

  constructor(private readonly item: Item, public key?: Key, plain?: Entity) {}

  get first(): Item { return this.item; }
  set first(v: Item) {}
  run?(x: Options): void;
  over(x: Item): Key;
  over(x: Key): Item;
  over(x: Item | Key): Item | Key { return x; }
  pick<R extends Options>(x: R, y: Leaf): R { return x; }
  guard(x: unknown): asserts this is Shapes {}
  cond<X>(x: X): X extends (a: Item) => infer R ? R : Key { return undefined as never; }
  opt(opts: { Item: string; cb?: (Key: number) => Leaf } = { Item: "" }): void {}
}

export interface Sigs extends Omit<Options, "a">, Face<Key> {
  <T>(x: T): Item;
  new (x: Key): Leaf;
  get x(): Entity;
  m?(x: Item): void;
  readonly [index: number]: Logger;
}

export class Sub extends Base<Item, ns.Deep> implements Face<Leaf> {
  get(): Leaf { return new Leaf(); }
}

export class Sub2 extends Base<typeof Item> {}

function Mixin<TBase extends new (...args: any[]) => object>(B: TBase) {
  return class extends B {};
}

export class Mixed extends Mixin(Entity) {
  held?: Key;
}

export class Arr extends Array<Item> {}
