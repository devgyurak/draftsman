export class Zed {}
export class Ctx {}
export interface Handler {
  // #59: a `this` parameter names its type
  handle(this: Ctx, x: number): void;
}
export abstract class Base {
  abstract run(this: Zed): void;
}
export class A {
  m(this: Zed): void {}
  cb?: (this: Ctx, z: Zed) => void;
  self(this: A): A { return this; }
}
