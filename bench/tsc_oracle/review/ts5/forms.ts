import { Item, Key, Zed } from "./model";

export class A {
  m(this: Zed, x: Item): void {}
  n(this: A, y: Key): Item { return new Item(); }
  o?: (this: Zed) => void;
  static p(this: typeof Item): void {}
  q(this: void, z: Key): void {}
}

export interface I {
  f(this: Zed): Key;
}
