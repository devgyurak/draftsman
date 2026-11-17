import { BaseEntity, EntityRef, RefMap } from '../common';
import type { OrderId } from './order';
import type { Order } from './order';

export class Customer extends BaseEntity {
  name: string = '';
  private orders: Order[] = [];
  address: Customer.Address | null = null;
  listener?: BaseEntity.Listener;
  ref?: EntityRef;          // through `export type *`
  refs?: RefMap;            // a type alias: nothing to draw
  lastOrder?: OrderId;      // a type alias from another module

  isNew(): boolean {
    return this.id === undefined;
  }
}

export namespace Customer {
  export class Address {
    street = '';
  }
}
