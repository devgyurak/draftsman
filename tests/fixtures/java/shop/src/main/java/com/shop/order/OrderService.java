package com.shop.order;

import com.shop.customer.Customer;
import com.shop.pay.PaymentGateway;
import com.shop.pay.Receipt;
import java.util.List;

@Service
public class OrderService {
    private final OrderRepository repository;
    private final PaymentGateway gateway;

    public OrderService(OrderRepository repository, PaymentGateway gateway) {
        this.repository = repository;
        this.gateway = gateway;
    }

    public Order place(Customer customer, List<OrderLine> lines) {
        Order order = new Order() {
            @Override public boolean isNew() { return true; }
        };
        return repository.save(order);
    }

    public Receipt pay(Order order) {
        return gateway.charge(order);
    }

    public <T extends Order> T reload(T order) { return order; }

    @Override
    public String toString() { return "OrderService"; }
}
