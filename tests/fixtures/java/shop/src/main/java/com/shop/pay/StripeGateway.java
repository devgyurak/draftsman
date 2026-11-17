package com.shop.pay;

import com.shop.order.Order;
import com.stripe.*;

public class StripeGateway implements PaymentGateway {
    private StripeClient client;
    private Receipt.Money fee;

    @Override
    public Receipt charge(Order order) {
        return null;
    }
}
