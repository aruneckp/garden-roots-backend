-- Migration 31: Add Banginapalli 4 KG product

INSERT INTO products (name, description, origin, season_start, season_end, tag, image_url, emoji, is_active, display_order)
VALUES (
  'Banginapalli 4 KG',
  'Golden yellow colour with smooth, fiberless texture. A convenient 4 kg pack of the classic Banginapalli variety.',
  'Andhra Pradesh',
  'Apr', 'Jun',
  'Classic',
  '/banginapalli.jpg',
  '🍋',
  1,
  (SELECT NVL(MAX(display_order), 0) + 10 FROM products)
);
COMMIT;

INSERT INTO product_variants (product_id, size_name, unit, box_weight)
VALUES (
  (SELECT id FROM products WHERE name = 'Banginapalli 4 KG'),
  'Standard', 'box', 4
);
COMMIT;

INSERT INTO stock_inventory (product_variant_id, quantity_available, reserved_quantity, warehouse_location)
VALUES (
  (SELECT id FROM product_variants WHERE product_id = (SELECT id FROM products WHERE name = 'Banginapalli 4 KG')),
  0, 0, 'Main Warehouse - Singapore'
);
COMMIT;
