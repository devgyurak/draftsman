package com.shop.customer;

import com.shop.common.BaseEntity;
import com.shop.order.Order;
import java.util.List;
import java.util.ArrayList;

public class Customer extends BaseEntity {
    private String name;
    private final List<Order> orders = new ArrayList<>();
    private Address address;
    private Listener listener;   // inherited member type: BaseEntity.Listener

    public static class Address {
        String street;
        String city;
    }

    public boolean isNew() { return id == null; }

    public List<Order> getOrders() { return orders; }
}
