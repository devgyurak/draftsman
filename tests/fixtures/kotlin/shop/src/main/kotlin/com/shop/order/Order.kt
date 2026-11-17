package com.shop.order

import com.shop.common.BaseEntity
import com.shop.promo.*

enum class Status(val code: Int) {
    NEW(1), PAID(2) { override fun terminal() = true }, SHIPPED(3);

    open fun terminal() = false
}

class Order(var customer: Customer, constructorOnly: Int = 0) : BaseEntity() {
    private val lines: List<OrderLine> = emptyList()
    var status: Status = Status.NEW
    var coupon: Coupon? = null

    override fun isNew() = status == Status.NEW

    // a nested type naming a member type its enclosing class inherits
    class Audit : Listener {
        override fun changed(entity: BaseEntity) {}
    }

    fun addLine(line: OrderLine) {
        val f = { x: OrderLine -> x }
        f(line)
    }

    companion object {
        val EMPTY: Order? = null
        fun create(customer: Customer): Order = Order(customer)
    }
}

data class OrderLine(val product: Product, val quantity: Int)

data class Product(val sku: String, val price: Double)
