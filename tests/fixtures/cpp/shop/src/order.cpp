#include "shop/order.h"

namespace shop {

Customer::Customer(std::string name) : name_(std::move(name)) {}

bool Customer::isNew() const { return id_ == 0; }

Order::Order(Customer* customer) : customer_(customer) {}

bool Order::isNew() const { return status_ == Status::New; }

void Order::addLine(const OrderLine& line) {
    struct Local { int x; };
    auto f = [](const OrderLine& l) { return l.quantity; };
    lines_.push_back(line);
}

}  // namespace shop
