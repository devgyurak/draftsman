package com.shop.pay;

import com.shop.order.*;   // a project wildcard import

public interface PaymentGateway {
    Receipt charge(Order order);
    default boolean supportsRefund() { return false; }
}
