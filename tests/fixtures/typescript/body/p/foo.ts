import { Inner } from "./inner";

export class Foo {
  static X = 1;
  static create(): Foo {
    return new Foo();                         //> Foo=p/foo.Foo/r
  }
  // the class does not see the types of its merged namespace by their simple names
  inner(): Inner {
    return new Inner();                       //> Inner=p/inner.Inner/r
  }
}
// a namespace merged with the class: `Foo.Inner`
export namespace Foo {
  export class Inner {}
}
export interface Shape {
  area(): number;
}
export enum Kind { A, B }
export type Alias = Foo;
// a value and a type of one name: in a value position `Token` is the constant
export const Token = "token";
export interface Token {
  t: string;
}
export function decorate(...args: unknown[]): any {
  return () => args;
}
