import { BaseEntity } from '../common/base-entity';
import { Customer } from './customer';
import { Coupon } from '@shop/promotions';
import { Receipt } from '@shop/pay';   // a workspace package (src/pay/package.json)

export enum Status { New, Paid, Shipped }

export class Order extends BaseEntity {
  customer!: Customer;
  private lines: Array<OrderLine> = [];
  status: Status = Status.New;
  coupon?: Coupon;
  receipt?: Receipt;

  isNew(): boolean {
    return this.status === Status.New;
  }

  addLine(line: OrderLine): void {
    const add = (l: OrderLine) => this.lines.push(l);
    add(line);
  }
}

export class OrderAudit implements BaseEntity.Listener {
  changed(entity: BaseEntity): void {}
}

export class OrderLine {
  constructor(public readonly product: Product, public quantity: number) {}
}

export interface Product {
  sku: string;
  price: number;
}

export type OrderId = string;
