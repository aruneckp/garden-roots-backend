-- Add display-only fields to products so image and emoji are DB-sourced,
-- not hardcoded in frontend static files.
ALTER TABLE products ADD image_url VARCHAR(500);
ALTER TABLE products ADD emoji     VARCHAR(20);

-- Back-fill existing products by name
UPDATE products SET image_url = '/alphonso.jpg',      emoji = '🥭' WHERE name = 'Alphonso';
UPDATE products SET image_url = '/image1.png',        emoji = '🟡' WHERE name = 'Mallika';
UPDATE products SET image_url = '/banginapalli.jpg',  emoji = '🍋' WHERE name = 'Banganapalli';
UPDATE products SET image_url = '/imam_pasand.jpg',   emoji = '🔴' WHERE name = 'Imam Pasand';
UPDATE products SET image_url = '/Kesar.png',         emoji = '🟠' WHERE name = 'Kesar';
UPDATE products SET image_url = '/himayat.jpg',       emoji = '💛' WHERE name = 'Himayat';
