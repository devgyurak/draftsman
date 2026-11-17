package com.shop.common;

import java.time.Instant;

public interface Auditable {
    Instant createdAt();
}
