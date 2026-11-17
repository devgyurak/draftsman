package com.shop.common

import java.time.Instant

interface Auditable {
    val createdAt: Instant
}

abstract class BaseEntity : Auditable {
    protected var id: Long? = null
    override val createdAt: Instant = Instant.now()
    abstract fun isNew(): Boolean

    interface Listener {
        fun changed(entity: BaseEntity)
    }
}
