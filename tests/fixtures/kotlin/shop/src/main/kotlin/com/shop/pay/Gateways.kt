package com.shop.pay

import com.shop.order.*   // a project wildcard import
import com.stripe.*
import java.io.Closeable

interface PaymentGateway {
    suspend fun charge(order: Order): Receipt
    fun supportsRefund(): Boolean = false
}

class StripeGateway : PaymentGateway, Closeable {
    private lateinit var client: StripeClient
    private val fee: Receipt.Money? = null

    override suspend fun charge(order: Order): Receipt = TODO()
    override fun close() {}
    fun parse(text: String, parser: Receipt.Companion.Parser): Receipt = TODO()
}

data class Receipt(val id: String, val amount: Money) {
    data class Money(val cents: Long, val currency: String)

    companion object {
        class Parser   // Receipt.Parser, also named Receipt.Companion.Parser
    }
}

object GatewayRegistry {
    val gateways: Map<String, PaymentGateway> = emptyMap()
}
