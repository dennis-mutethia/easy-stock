-- Dumping data for table packages
INSERT INTO packages (name, amount, pay, description, offer, color, validity) VALUES
('7-DAY TRIAL', 0, 0, 'FREE TRIAL PERIOD', '', 'danger', 7),
('1-MONTH', 1000, 1000, '1 MONTH BASIC PREMIUM PACKAGE', 'STARTER', 'success', 31),
('3-MONTHS', 3000, 3000, '3 MONTHS BRONZE PACKAGE', 'OPTIMIZED', 'warning', 93),
('6-MONTHS S.T.S', 6000, 5000, '6 MONTHS SHORT TERM SUPPORT', 'SAVE UPTO 10%', 'primary', 186),
('1-YEAR L.T.S', 12000, 9000, '1 YEAR LONG TERM SUPPORT', 'SAVE UPTO 15%', 'secondary', 366),
('2-YEARS L.T.S', 24000, 16000, '2 YEARS LONG TERM SUPPORT', 'SAVE UPTO 20%', 'info', 732),
('3-YEARS L.T.S', 36000, 24000, '3 YEARS LONG TERM SUPPORT', 'SAVE UPTO 30%', 'success', 1098)
ON CONFLICT (name) DO NOTHING;

-- Dumping data for table shop_types
INSERT INTO shop_types (name) VALUES
('WINES & SPIRITS / BAR'),
('PHARMACY / CHEMIST'),
('AGROVET'),
('HARDWARE'),
('BUTCHERY'),
('GENERAL SHOP'),
('AUTO SPARE PARTS'),
('BOUTIQUE'),
('CAR DEALER'),
('COSMETIC & BEAUTY'),
('PETROL STATION'),
('GREEN GROCERY')
ON CONFLICT (name) DO NOTHING;

-- Dumping data for table user_levels
INSERT INTO user_levels (name, description) VALUES
('SUPER ADMIN', 'All Permissions<br />Can access admin portal'),
('ADMIN', 'All Permissions<br />Can Navigate Multiple Shops'),
('SUPERVISOR', 'Stock<br /> Inventory<br />Customer Bills<br />Expenses<br />\nCan Navigate Multiple Shops'),
('SALES', 'Stock<br /> Inventory<br />Customer Bills<br />\nExpenses<br />\nCannot Navigate Multiple Shops'),
('DIRECTOR', 'View Reports Only<br />Can Navigate Multiple Shops')
ON CONFLICT (name) DO NOTHING;

-- Dumping data for table payment_modes
INSERT INTO payment_modes (name, account, shop_id) VALUES
('CASH', NULL, 1),
('MPESA', NULL, 1)
ON CONFLICT (name) DO NOTHING;
