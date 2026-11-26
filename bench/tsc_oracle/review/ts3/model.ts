export interface Options { a?: number }
export interface Logger { log(): void }
export class Item {}
export class Key {}
export class Entity {}
export class Leaf {}
export enum Color { Red = "red", Blue = "blue" }
export namespace ns {
  export class Deep {}
  export namespace inner { export class Leaf {} }
}
export interface Face<T> { get(): T }
export class Base<A, B = Key> { a?: A; b?: B }
export class R {}
export class F {}
export class Tree2 {}
export type Provider = Options | Logger;
export type Tree = { left?: Tree; value: Item };
