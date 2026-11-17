package com.shop.order;

import com.shop.customer.Customer;
import org.springframework.data.repository.CrudRepository;
import java.util.List;

public interface OrderRepository extends CrudRepository<Order, Long> {
    List<Order> findByCustomer(Customer customer);
}
