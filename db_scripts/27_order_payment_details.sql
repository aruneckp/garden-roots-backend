-- Migration 27: Add payment detail fields to orders
-- Tracks actual price charged, comments, who received, who updated, and collection status

ALTER TABLE orders
  ADD  actual_price NUMERIC(10, 2);

ALTER TABLE orders
  ADD  payment_comments VARCHAR2(4000);

ALTER TABLE orders
  ADD  payment_received_by VARCHAR(150);

ALTER TABLE orders
  ADD  payment_updated_by VARCHAR(150);

ALTER TABLE orders
  ADD  payment_collection_status VARCHAR(50) DEFAULT 'to_be_received';
