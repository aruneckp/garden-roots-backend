-- Migration 32: Add Chinna Rasalu product

INSERT INTO products (name, description, origin, season_start, season_end, tag, image_url, emoji, is_active, display_order)
VALUES (
  'Chinna Rasalu',
  'A small, intensely sweet mango prized for its rich juice and honey-like flavour. A beloved heirloom variety from Andhra Pradesh.',
  'Andhra Pradesh',
  'May', 'Jun',
  'Heirloom',
  '/chinna_rasalu.jpg',
  '🍯',
  1,
  (SELECT NVL(MAX(display_order), 0) + 10 FROM products)
);
COMMIT;

INSERT INTO product_variants (product_id, size_name, unit, box_weight)
VALUES (
  (SELECT id FROM products WHERE name = 'Chinna Rasalu'),
  'Standard', 'box', 5
);
COMMIT;

INSERT INTO stock_inventory (product_variant_id, quantity_available, reserved_quantity, warehouse_location)
VALUES (
  (SELECT id FROM product_variants WHERE product_id = (SELECT id FROM products WHERE name = 'Chinna Rasalu')),
  0, 0, 'Main Warehouse - Singapore'
);
COMMIT;
