#pragma once
#include <string>
#include "shop/order.h"

namespace shop::pay {

struct Receipt {
    struct Money {
        long cents;
        std::string currency;
    };
    std::string id;
    Money amount;
};

class PaymentGateway {
public:
    virtual ~PaymentGateway() = default;
    virtual Receipt charge(const Order& order) = 0;
    virtual bool supportsRefund() const { return false; }
};

class StripeGateway final : public PaymentGateway, private stripe::ClientHolder {
public:
    Receipt charge(const Order& order) override;

private:
    stripe::StripeClient* client_ = nullptr;
    Receipt::Money fee_{};
};

}  // namespace shop::pay
