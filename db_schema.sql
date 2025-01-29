-- Table structure for table packages
DROP TABLE IF EXISTS packages;
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
DROP TABLE IF EXISTS licenses;
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
DROP TABLE IF EXISTS companies;
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
DROP TABLE IF EXISTS shop_types;
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
DROP TABLE IF EXISTS shops;
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
DROP TABLE IF EXISTS user_levels;
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
DROP TABLE IF EXISTS users;
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
DROP TABLE IF EXISTS product_categories;
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
DROP TABLE IF EXISTS products;
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
DROP TABLE IF EXISTS stock;
CREATE TABLE IF NOT EXISTS stock (
  id SERIAL NOT NULL,
  stock_date DATE NOT NULL,
  product_id INT NOT NULL,
  shop_id INT NOT NULL,
  name TEXT,
  category_id INT,
  purchase_price DOUBLE PRECISION,
  selling_price DOUBLE PRECISION,
  opening DOUBLE PRECISION,
  additions DOUBLE PRECISION,
  created_at TIMESTAMP,
  created_by INT,
  updated_at TIMESTAMP,
  updated_by INT,
  PRIMARY KEY (stock_date, product_id, shop_id) -- Includes the partitioning column
) PARTITION BY RANGE (stock_date);

-- Table structure for table customers
DROP TABLE IF EXISTS customers;
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

-- Table structure for table bills
DROP TABLE IF EXISTS bills;
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

-- Table structure for table expenses
DROP TABLE IF EXISTS expenses;
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
DROP TABLE IF EXISTS payment_modes;
CREATE TABLE IF NOT EXISTS payment_modes (
  id SERIAL PRIMARY KEY,
  name TEXT,
  created_at TIMESTAMP,
  created_by INT,
  updated_at TIMESTAMP,
  updated_by INT,
  UNIQUE(name)
);

-- Table structure for table payments
DROP TABLE IF EXISTS payments;
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
DROP TABLE IF EXISTS cashbox;
CREATE TABLE IF NOT EXISTS cashbox (
  id SERIAL PRIMARY KEY,
  date date,
  cash DOUBLE PRECISION,
  mpesa DOUBLE PRECISION,
  shop_id INT,
  created_at TIMESTAMP,
  created_by INT,
  updated_at TIMESTAMP,
  updated_by INT,
  UNIQUE (date, shop_id)
);
