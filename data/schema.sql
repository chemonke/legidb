CREATE DATABASE IF NOT EXISTS legidb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE legidb;

CREATE TABLE IF NOT EXISTS food_categories (
  id INT AUTO_INCREMENT PRIMARY KEY,
  ref_no VARCHAR(32) NOT NULL,
  description VARCHAR(255) NOT NULL,
  acidic BOOLEAN,
  frf INT
);

CREATE TABLE IF NOT EXISTS foods (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255),
  food_category_id INT NOT NULL,
  FOREIGN KEY (food_category_id) REFERENCES food_categories(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS simulants (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  abbreviation VARCHAR(16) NOT NULL
);

CREATE TABLE IF NOT EXISTS food_category_simulants (
  food_category_id INT NOT NULL,
  simulant_id INT NOT NULL,
  PRIMARY KEY (food_category_id, simulant_id),
  UNIQUE KEY unique_food_sim (food_category_id, simulant_id),
  FOREIGN KEY (food_category_id) REFERENCES food_categories(id) ON DELETE CASCADE,
  FOREIGN KEY (simulant_id) REFERENCES simulants(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS substances (
  id INT AUTO_INCREMENT PRIMARY KEY,
  smiles VARCHAR(255),
  cas_no VARCHAR(64),
  fcm_no INT,
  ec_ref_no INT
);

CREATE TABLE IF NOT EXISTS sm_entries (
  id INT AUTO_INCREMENT PRIMARY KEY,
  substance_id INT NOT NULL,
  fcm_no INT,
  use_as_additive_or_ppa BOOLEAN NOT NULL,
  use_as_monomer_or_starting_substance BOOLEAN NOT NULL,
  frf_applicable BOOLEAN NOT NULL,
  restrictions_and_specifications TEXT,
  FOREIGN KEY (substance_id) REFERENCES substances(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sm_entry_limits (
  id INT AUTO_INCREMENT PRIMARY KEY,
  sm_entry_id INT NOT NULL,
  kind ENUM('SML','ND') NOT NULL,
  value DECIMAL(10,3),
  unit_basis ENUM('FOOD_KG','ARTICLE','SURFACE_DM2') NOT NULL DEFAULT 'FOOD_KG',
  raw_expression VARCHAR(64),
  UNIQUE KEY unique_sm_kind (sm_entry_id, kind),
  FOREIGN KEY (sm_entry_id) REFERENCES sm_entries(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS annex1_group_restrictions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  group_restriction_no INT NOT NULL UNIQUE,
  total_limit_value DECIMAL(10,3),
  unit_basis ENUM('FOOD_KG','ARTICLE','SURFACE_DM2') NOT NULL DEFAULT 'FOOD_KG',
  specification TEXT
);

CREATE TABLE IF NOT EXISTS sm_entry_group_restrictions (
  sm_id INT NOT NULL,
  group_restriction_id INT NOT NULL,
  PRIMARY KEY (sm_id, group_restriction_id),
  UNIQUE KEY unique_sm_group (sm_id, group_restriction_id),
  FOREIGN KEY (sm_id) REFERENCES sm_entries(id) ON DELETE CASCADE,
  FOREIGN KEY (group_restriction_id) REFERENCES annex1_group_restrictions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sm_conditions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  worst_case_time INT,
  testing_time INT,
  worst_case_temp INT,
  testing_temp INT
);
