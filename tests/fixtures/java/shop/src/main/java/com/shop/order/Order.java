package com.shop.order;

import com.shop.common.BaseEntity;
import com.shop.customer.Customer;
import java.util.*;

@Entity
public class Order extends BaseEntity {
    private Customer customer;
    private List<OrderLine> lines = new ArrayList<>();
    private Status status = Status.NEW;
    private Optional<Coupon> coupon;

    public enum Status {
        NEW, PAID, SHIPPED {
            @Override boolean terminal() { return true; }
        };

        boolean terminal() { return false; }
    }

    public boolean isNew() { return status == Status.NEW; }

    // a nested type naming a member type its enclosing class inherits
    static class Audit implements Listener {
        public void changed(BaseEntity entity) {}
    }

    public void addLine(OrderLine line) {
        Runnable r = () -> lines.add(line);
        r.run();
    }
}
