USE legidb;

INSERT INTO food_categories (ref_no, description, acidic, frf) VALUES
('01.01', 'Non-processed food for infants and young children', 0, 3),
('01.02', 'Processed cereal-based food for infants and young children', 0, 3),
('02.01', 'Fruit juices and nectars', 1, 1),
('03.01', 'Milk and dairy products', 0, 1);

INSERT INTO simulants (name, abbreviation) VALUES
('Simulant A - Ethanol 10%', 'A'),
('Simulant B - Acetic acid 3%', 'B'),
('Simulant D1 - Ethanol 50%', 'D1'),
('Simulant D2 - Sunflower oil', 'D2');

INSERT INTO food_category_simulants (food_category_id, simulant_id) VALUES
(1, 1), (1, 2),
(2, 1), (2, 2), (2, 3),
(3, 1), (3, 2), (3, 4),
(4, 1), (4, 4);

INSERT INTO foods (name, food_category_id) VALUES
('Infant formula', 1),
('Baby cereal', 2),
('Apple juice', 3),
('Whole milk', 4);

INSERT INTO substances (smiles, cas_no, fcm_no, ec_ref_no) VALUES
('C2H4', '74-85-1', 100, 200),
('C3H6O', '67-64-1', 101, 201);

INSERT INTO sm_entries (substance_id, fcm_no, use_as_additive_or_ppa, use_as_monomer_or_starting_substance, frf_applicable, restrictions_and_specifications) VALUES
(1, 100, 0, 1, 1, 'Use as monomer; FRF applies'),
(2, 101, 1, 0, 0, 'Additive; no FRF');

INSERT INTO sm_entry_limits (sm_entry_id, kind, value, unit_basis, raw_expression) VALUES
(1, 'SML', 5.0, 'FOOD_KG', '5'),
(2, 'ND', NULL, 'FOOD_KG', 'ND');

INSERT INTO annex1_group_restrictions (group_restriction_no, total_limit_value, unit_basis, specification) VALUES
(1, 60.0, 'FOOD_KG', 'Group 1 example');

INSERT INTO sm_entry_group_restrictions (sm_id, group_restriction_id) VALUES
(1, 1);
