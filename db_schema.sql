-- Table structure for table packages
CREATE TABLE IF NOT EXISTS packages (
  id SERIAL PRIMARY KEY,
  name TEXT,
  amount DOUBLE PRECISION,
  pay DOUBLE PRECISION,
  description TEXT,
  offer TEXT,
  color TEXT,
  validity INT,
  created_at TIMESTAMP,
  created_by INT,
  updated_at TIMESTAMP,
  updated_by INT,
  UNIQUE (name)
);

-- Table structure for table licenses
CREATE TABLE IF NOT EXISTS licenses (
  id SERIAL PRIMARY KEY,
  key TEXT,
  package_id INT,
  expires_at TIMESTAMP,
  payment_id INT,
  created_at TIMESTAMP,
  created_by INT,
  updated_at TIMESTAMP,
  updated_by INT,
  UNIQUE (key)
);

-- Table structure for table companies
CREATE TABLE IF NOT EXISTS companies (
  id SERIAL PRIMARY KEY,
  name TEXT,
  license_id INT,
  created_at TIMESTAMP,
  created_by INT,
  updated_at TIMESTAMP,
  updated_by INT
);

-- Table structure for table shop_types
CREATE TABLE IF NOT EXISTS shop_types (
  id SERIAL PRIMARY KEY,
  name TEXT,
  description TEXT,
  created_at TIMESTAMP,
  created_by INT,
  updated_at TIMESTAMP,
  updated_by INT,
  UNIQUE (name)
);

-- Table structure for table shops
CREATE TABLE IF NOT EXISTS shops (
  id SERIAL PRIMARY KEY,
  name TEXT,
  location TEXT,
  company_id INT,
  shop_type_id INT,
  created_at TIMESTAMP,
  created_by INT,
  updated_at TIMESTAMP,
  updated_by INT,
  phone_1 TEXT,
  phone_2 TEXT,
  paybill TEXT,
  account_no TEXT,
  till_no TEXT
);

-- Table structure for table user_levels
CREATE TABLE IF NOT EXISTS user_levels (
  id SERIAL PRIMARY KEY,
  name TEXT,
  level INT DEFAULT '0',
  description TEXT,
  created_at TIMESTAMP,
  created_by INT,
  updated_at TIMESTAMP,
  updated_by INT,
  UNIQUE (name)
);

-- Table structure for table users
CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  name TEXT,
  phone TEXT,
  shop_id INT,
  user_level_id INT DEFAULT '0',
  password TEXT,
  created_at TIMESTAMP,
  created_by INT,
  updated_at TIMESTAMP,
  updated_by INT,
  UNIQUE (phone)
);

-- Table structure for table product_categories
CREATE TABLE IF NOT EXISTS product_categories (
  id SERIAL PRIMARY KEY,
  name TEXT,
  shop_id INT,
  created_at TIMESTAMP,
  created_by INT,
  updated_at TIMESTAMP,
  updated_by INT,
  UNIQUE (name, shop_id)
);

-- Table structure for table products
CREATE TABLE IF NOT EXISTS products (
  id SERIAL PRIMARY KEY,
  name TEXT,
  purchase_price DOUBLE PRECISION,
  selling_price DOUBLE PRECISION,
  category_id INT,
  shop_id INT,
  created_at TIMESTAMP,
  created_by INT,
  updated_at TIMESTAMP,
  updated_by INT,
  UNIQUE (name, shop_id)
);

-- Table structure for table stock
CREATE TABLE IF NOT EXISTS stock (
  id SERIAL PRIMARY KEY,
  stock_date date,
  product_id INT,
  name TEXT,
  category_id INT,
  purchase_price DOUBLE PRECISION,
  selling_price DOUBLE PRECISION,
  opening DOUBLE PRECISION,
  additions DOUBLE PRECISION,
  shop_id INT,
  created_at TIMESTAMP,
  created_by INT,
  updated_at TIMESTAMP,
  updated_by INT,
  UNIQUE (stock_date,product_id,shop_id)
);

-- Table structure for table bills
CREATE TABLE IF NOT EXISTS bills (
  id SERIAL PRIMARY KEY,
  customer_id INT,
  total DOUBLE PRECISION,
  paid DOUBLE PRECISION,
  shop_id INT,
  created_at TIMESTAMP,
  created_by INT,
  updated_at TIMESTAMP,
  updated_by INT
);

-- Table structure for table bill_entries
CREATE TABLE IF NOT EXISTS bill_entries (
  id SERIAL PRIMARY KEY,
  bill_id INT,
  stock_id INT,
  item_name TEXT,
  price DOUBLE PRECISION,
  qty DOUBLE PRECISION,
  shop_id INT,
  created_at TIMESTAMP,
  created_by INT,
  updated_at TIMESTAMP,
  updated_by INT,
  UNIQUE (bill_id,stock_id,created_by)
);

-- Table structure for table customers
CREATE TABLE IF NOT EXISTS customers (
  id SERIAL PRIMARY KEY,
  name TEXT,
  phone TEXT,
  shop_id INT,
  created_at TIMESTAMP,
  created_by INT,
  updated_at TIMESTAMP,
  updated_by INT,
  UNIQUE (phone, shop_id)
);

-- Table structure for table expenses
CREATE TABLE IF NOT EXISTS expenses (
  id SERIAL PRIMARY KEY,
  date date,
  name TEXT,
  amount DOUBLE PRECISION,
  shop_id INT,
  created_at TIMESTAMP,
  created_by INT,
  updated_at TIMESTAMP,
  updated_by INT
);

-- Table structure for table payment_modes
CREATE TABLE IF NOT EXISTS payment_modes (
  id SERIAL PRIMARY KEY,
  name TEXT,
  account TEXT,
  shop_id INT,
  created_at TIMESTAMP,
  created_by INT,
  updated_at TIMESTAMP,
  updated_by INT,
  UNIQUE(name)
);

-- Table structure for table payments
CREATE TABLE IF NOT EXISTS payments (
  id SERIAL PRIMARY KEY,
  bill_id INT,
  amount DOUBLE PRECISION,
  payment_mode_id INT,
  shop_id INT,
  created_at TIMESTAMP,
  created_by INT,
  updated_at TIMESTAMP,
  updated_by INT
);

-- Table structure for table cashbox
CREATE TABLE IF NOT EXISTS cashbox (
  id SERIAL PRIMARY KEY,
  date date,
  amount DOUBLE PRECISION,
  shop_id INT,
  created_at TIMESTAMP,
  created_by INT,
  updated_at TIMESTAMP,
  updated_by INT,
  UNIQUE (date)
);
