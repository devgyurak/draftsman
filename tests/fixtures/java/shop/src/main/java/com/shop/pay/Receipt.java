package com.shop.pay;

public record Receipt(String id, Money amount) {
    public record Money(long cents, String currency) {}
}
