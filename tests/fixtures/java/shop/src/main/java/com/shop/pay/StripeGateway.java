package com.shop.pay;

import com.shop.order.Order;
import com.stripe.*;

public class StripeGateway implements PaymentGateway {
    private StripeClient client;
    private Receipt.Money fee;

    @Override
    public Receipt charge(Order order) {
        if (fee == null) {
            fee = new Receipt.Money(0, "usd");   // a name in a body: the only dependency on Money
        }
        return null;
    }
}
