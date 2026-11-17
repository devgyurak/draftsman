package com.shop.order

import com.shop.pay.PaymentGateway
import com.shop.pay.Receipt
import org.springframework.data.repository.CrudRepository

interface OrderRepository : CrudRepository<Order, Long> {
    fun findByCustomer(customer: Customer): List<Order>
}

class OrderService(
    private val repository: OrderRepository,
    private val gateway: PaymentGateway,
) {
    fun place(customer: Customer, lines: List<OrderLine>): Order = TODO()

    suspend fun pay(order: Order): Receipt = gateway.charge(order)

    fun <T : Order> reload(order: T): T = order
}

fun Order.total(): Int = 0
