#pragma once
#include <memory>
#include <vector>
#include "shop/order.h"

namespace shop {
namespace pay {
class PaymentGateway;
struct Receipt;
}  // namespace pay

template <typename T>
class Repository {
public:
    virtual ~Repository() = default;
    virtual std::vector<T*> findAll() = 0;
};

class OrderRepository : public Repository<Order> {
public:
    virtual std::vector<Order*> findByCustomer(const Customer& customer) = 0;
};

class OrderService {
public:
    OrderService(std::shared_ptr<OrderRepository> repository, pay::PaymentGateway& gateway);
    Order place(const Customer& customer, const std::vector<OrderLine>& lines);
    pay::Receipt pay(const Order& order);

    template <typename T>
    T reload(T order) { return order; }

private:
    std::shared_ptr<OrderRepository> repository_;
    pay::PaymentGateway& gateway_;
    detail::Cache<Order> cache_;
};

}  // namespace shop
