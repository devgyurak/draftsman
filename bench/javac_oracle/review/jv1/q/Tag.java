package q; public @interface Tag { Kind value(); Class<?> type() default Object.class; }
