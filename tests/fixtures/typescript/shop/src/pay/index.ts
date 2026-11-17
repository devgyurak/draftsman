import { Order } from '../order/order';
import { StripeClient } from 'stripe';

export interface PaymentGateway {
  charge(order: Order): Promise<Receipt>;
  supportsRefund?(): boolean;
}

export class StripeGateway implements PaymentGateway {
  #client: StripeClient;
  private fee: Receipt.Money | undefined;

  constructor(client: StripeClient) {
    this.#client = client;
  }

  async charge(order: Order): Promise<Receipt> {
    return new Receipt();
  }
}

export class Receipt {
  id = '';
  amount?: Receipt.Money;
}

export namespace Receipt {
  export interface Money {
    cents: number;
    currency: string;
  }
}
