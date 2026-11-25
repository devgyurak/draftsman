// project types the forms name, and rivals named like what is no type name there
export interface Options { a?: number }
export interface Logger { log(): void }
export class Item {}
export class Key {}
export class Foo {}
export enum Color { Red = "red" }
// rivals of type parameters, `infer U` and a mapped type's key
export class T {}
export class U {}
export class K {}
export class Store {
  Logger = 1;
  Item = "";
}
