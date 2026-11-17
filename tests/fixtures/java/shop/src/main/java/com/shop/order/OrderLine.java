package com.shop.order;

import com.shop.catalog.Product;

public record OrderLine(Product product, int quantity) {
    public OrderLine {
        if (quantity <= 0) throw new IllegalArgumentException();
    }
}
