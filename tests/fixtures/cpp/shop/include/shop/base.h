#pragma once
#include <cstdint>
#include <ctime>

namespace shop {

class Auditable {
public:
    virtual ~Auditable() = default;
    virtual std::time_t createdAt() const = 0;
};

class BaseEntity : public Auditable {
public:
    std::time_t createdAt() const override { return created_; }
    virtual bool isNew() const = 0;

    struct Listener {
        virtual ~Listener() = default;
        virtual void changed(BaseEntity& entity) = 0;
    };

protected:
    std::int64_t id_ = 0;

private:
    std::time_t created_ = 0;
};

}  // namespace shop
