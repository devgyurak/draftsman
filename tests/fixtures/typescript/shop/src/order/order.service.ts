import { Injectable } from '@nestjs/common';
import { Repository } from 'typeorm';
import * as pay from '../pay';
import { Order, OrderLine } from './order';
import { Customer } from './customer';

export interface OrderRepository extends Repository<Order> {
  findByCustomer(customer: Customer): Promise<Order[]>;
}

@Injectable()
export class OrderService {
  static instance?: OrderService;

  constructor(
    private readonly repository: OrderRepository,
    private readonly gateway: pay.PaymentGateway,
  ) {}

  place(customer: Customer, lines: OrderLine[]): Order {
    return new Order();
  }

  async pay(order: Order): Promise<pay.Receipt> {
    return this.gateway.charge(order);
  }

  reload<T extends Order>(order: T): T {
    return order;
  }
}
