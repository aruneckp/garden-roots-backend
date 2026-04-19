
delete from pickup_locations;

-- Melville Park
INSERT INTO pickup_locations (name, address, phone, whatsapp_phone, email, manager_name, location_type, capacity, collection_hours, is_active)
VALUES ('Melville Park', '#06-15, Blk 28, Melville Park, Simei Street 1, 529948', '86222164‬', '86222164‬', 'help@garden-roots.com', 'Shiva', 'retail', 100,  'Mon–Sun: 10am–10pm', 1);

-- Punggol
INSERT INTO pickup_locations (name, address, phone, whatsapp_phone, email, manager_name, location_type, capacity, collection_hours, is_active)
VALUES ('Punggol', 'Blk-679A, #16-876, Near Damai LRT, Singapore 821679', '81601289', '6581601289', 'help@garden-roots.com', 'Venkat', 'retail', 100, 'Mon–Sat: 10am–10pm', 1);

-- Tampines West
INSERT INTO pickup_locations (name, address, phone, whatsapp_phone, email, manager_name, location_type, capacity, collection_hours, is_active)
VALUES ('Tampines West', 'Blk 929, Tampines Street 91, #13-443, Singapore 520929', '98346177', '6598346177', 'help@garden-roots.com', 'Venky', 'retail', 75, 'Mon–Sun: 10am–9pm', 1);

-- Sengkang
INSERT INTO pickup_locations (name, address, phone, whatsapp_phone, email, manager_name, location_type, capacity, collection_hours, is_active)
VALUES ('Sengkang', 'Blk 183C, #16-241, Rivervale Crescent, 543183', '96785432', '6581601289', 'help@garden-roots.com', 'Venkat', 'retail', 100, 'Mon–Sun: 10am–10pm', 1);

-- Punggol Walk - Twin Waterfalls
INSERT INTO pickup_locations (name, address, phone, whatsapp_phone, email, manager_name, location_type, capacity, collection_hours, is_active)
VALUES ('Punggol Walk - Twin Waterfalls', '118, #11-39, PUNGGOL WALK', '87264044', '6587264044', 'help@garden-roots.com', 'Venkata', 'retail', 100,  'Mon–Sun: 10am–10pm', 1);

-- Woodlands
INSERT INTO pickup_locations (name, address, phone, whatsapp_phone, email, manager_name, location_type, capacity, collection_hours, is_active)
VALUES ('Woodlands', 'BLK 724, #03-502, Woodlands Ave 6, 730724', '81601289', '6581601289', 'help@garden-roots.com', 'Srinivas Reddy', 'retail', 100, 'Mon–Sun: 10am–10pm', 1);

-- Serangoon
INSERT INTO pickup_locations (name, address, phone, whatsapp_phone, email, manager_name, location_type, capacity, collection_hours, is_active)
VALUES ('Serangoon', '141, #02-06, Serangoon North Ave 2, 550141', '91211028', '6591211028', 'help@garden-roots.com', 'Sashi', 'retail', 100,'Mon–Sun: 10am–10pm', 1);

COMMIT;



select *
from pickup_locations;
