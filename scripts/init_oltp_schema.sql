-- ============================================================
-- OLTP source schema — simulates the retailer's application DB.
-- Runs automatically once, on first container startup, via
-- Postgres's /docker-entrypoint-initdb.d/ mechanism.
-- Phase 1 only creates structure — Phase 2 generates and loads data.
-- ============================================================

CREATE TABLE IF NOT EXISTS customers (
    customer_id     BIGINT PRIMARY KEY,
    name            TEXT,
    email           TEXT,
    phone           TEXT,
    city            TEXT,
    state           TEXT,
    country         TEXT,
    signup_date     DATE,
    loyalty_tier    TEXT,
    updated_at      TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    product_id      BIGINT PRIMARY KEY,
    product_name    TEXT,
    category        TEXT,
    brand           TEXT,
    price           NUMERIC(10,2),
    cost            NUMERIC(10,2),
    updated_at      TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
    order_id        BIGINT PRIMARY KEY,
    customer_id     BIGINT REFERENCES customers(customer_id),
    order_date      TIMESTAMP,
    order_status    TEXT,
    order_amount    NUMERIC(10,2),
    payment_method  TEXT
);

CREATE TABLE IF NOT EXISTS order_items (
    order_item_id   BIGINT PRIMARY KEY,
    order_id        BIGINT REFERENCES orders(order_id),
    product_id      BIGINT REFERENCES products(product_id),
    quantity        INTEGER,
    unit_price      NUMERIC(10,2)
);

CREATE TABLE IF NOT EXISTS payments (
    payment_id      BIGINT PRIMARY KEY,
    order_id        BIGINT REFERENCES orders(order_id),
    payment_date    TIMESTAMP,
    payment_status  TEXT,
    amount          NUMERIC(10,2)
);

CREATE TABLE IF NOT EXISTS campaigns (
    campaign_id     BIGINT PRIMARY KEY,
    campaign_name   TEXT,
    channel         TEXT,
    budget          NUMERIC(10,2),
    start_date      DATE,
    end_date        DATE
);

-- Helpful indexes for the joins the batch pipeline will run later
CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items(product_id);
CREATE INDEX IF NOT EXISTS idx_payments_order_id ON payments(order_id);
