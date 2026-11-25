import { Node, Item, T, Options, Logger, Base, Cmp } from "./model";
import * as other from "./other";

export class NodeList extends Array<Node> {}
export class Gen<T> extends Array<T> {}
export interface Nested extends Map<string, Item[]> {}
export class UsesB extends Array<other.Node> {}
export class Sub extends Base<Item> implements Cmp<Sub> {
  cmp(o: Sub): number { return 0; }
}
export class Multi extends Base<
  { a: Item; b: Node }
> {}

// #25: project aliases named like containers
export type Provider = Options | Logger;
export type Vector = Item[];
export type Iterator = Node;
export class Holder {
  provider?: Provider;
  items?: Vector;
  it?: Iterator;
}
