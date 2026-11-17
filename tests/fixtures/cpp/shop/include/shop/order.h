#pragma once
#include <memory>
#include <optional>
#include <string>
#include <vector>
#include "shop/base.h"

namespace shop {

class Order;

enum class Status { New, Paid, Shipped };

struct Product {
    std::string sku;
    double price;
};

struct OrderLine {
    Product product;
    int quantity = 1;
};

class Customer : public BaseEntity {
public:
    struct Address {
        std::string street;
    };

    explicit Customer(std::string name);
    bool isNew() const override;

private:
    std::string name_;
    std::vector<Order*> orders_;
    std::unique_ptr<Address> address_;
    Listener* listener_ = nullptr;   // inherited member type: BaseEntity::Listener
};

class Order : public BaseEntity {
public:
    explicit Order(Customer* customer);
    bool isNew() const override;
    void addLine(const OrderLine& line);

    static const Order* empty();

    // a nested type naming a member type its enclosing class inherits
    struct Audit : Listener {
        void changed(BaseEntity& entity) override;
    };

private:
    Customer* customer_;
    std::vector<OrderLine> lines_;
    Status status_ = Status::New;
    std::optional<promo::Coupon> coupon_;
};

namespace detail {
template <typename T>
class Cache {
    std::vector<std::shared_ptr<T>> items_;
};
}  // namespace detail

}  // namespace shop
