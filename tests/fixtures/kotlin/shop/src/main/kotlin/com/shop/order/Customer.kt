package com.shop.order

import com.shop.common.BaseEntity

class Customer(val name: String, private val orders: MutableList<Order> = mutableListOf()) : BaseEntity() {
    var address: Address? = null
    var listener: Listener? = null   // inherited member type: BaseEntity.Listener

    data class Address(val street: String)

    override fun isNew(): Boolean = id == null
}
