CREATE DATABASE IF NOT EXISTS legidb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE legidb;

CREATE TABLE IF NOT EXISTS food_categories (
  id INT AUTO_INCREMENT PRIMARY KEY,
  ref_no VARCHAR(20) NOT NULL UNIQUE,
  description VARCHAR(255) NOT NULL,
  acidic BOOLEAN NOT NULL,
  frf INT
);

CREATE TABLE IF NOT EXISTS foods (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  food_category_id INT NOT NULL,
  FOREIGN KEY (food_category_id) REFERENCES food_categories(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS simulants (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  abbreviation VARCHAR(10) NOT NULL UNIQUE
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
  cas_no VARCHAR(20) NOT NULL UNIQUE,
  fcm_no INT NOT NULL UNIQUE,
  ec_ref_no INT NOT NULL
);

CREATE TABLE IF NOT EXISTS sm_entries (
  id INT AUTO_INCREMENT PRIMARY KEY,
  substance_id INT NOT NULL,
  fcm_no INT,
  use_as_additive_or_ppa BOOLEAN NOT NULL,
  use_as_monomer_or_starting_substance BOOLEAN NOT NULL,
  frf_applicable BOOLEAN NOT NULL,
  sml VARCHAR(255),
  restrictions_and_specifications TEXT,
  FOREIGN KEY (substance_id) REFERENCES substances(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS group_restrictions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  group_sml DECIMAL(18,6) NOT NULL,
  unit VARCHAR(30) NOT NULL,
  specification VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS sm_entry_group_restrictions (
  sm_id INT NOT NULL,
  group_restriction_id INT NOT NULL,
  PRIMARY KEY (sm_id, group_restriction_id),
  UNIQUE KEY unique_sm_group (sm_id, group_restriction_id),
  FOREIGN KEY (sm_id) REFERENCES sm_entries(id) ON DELETE CASCADE,
  FOREIGN KEY (group_restriction_id) REFERENCES group_restrictions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sm_time_conditions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  worst_case_time_minutes INT NOT NULL,
  testing_time_minutes INT NOT NULL
);

CREATE TABLE IF NOT EXISTS sm_temp_conditions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  worst_case_temp_celsius INT NOT NULL,
  testing_temp_celsius INT NOT NULL,
  note VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS plan_favorites (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  payload JSON NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
