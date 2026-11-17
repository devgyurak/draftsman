package com.shop.common;

import java.time.Instant;

public abstract class BaseEntity implements Auditable {
    protected Long id;
    private Instant createdAt;

    public Long getId() { return id; }

    @Override
    public Instant createdAt() { return createdAt; }

    public abstract boolean isNew();

    public interface Listener {
        void changed(BaseEntity entity);
    }
}
