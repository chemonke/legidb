USE legidb;

INSERT INTO food_categories (ref_no, description, acidic, frf) VALUES
('01.01A', 'Clear non-alcoholic drinks (water, infusions, soft drinks)', 1, 1),
('01.01B', 'Cloudy non-alcoholic drinks with pulp or chocolate', 1, 1),
('01.02', 'Alcoholic beverages between 6 % vol and 20 % vol', 0, 1),
('01.03', 'Alcoholic beverages above 20 % vol and cream liqueurs', 0, 1),
('02.01', 'Starches (dry powders)', 0, NULL),
('02.05A', 'Dry pastry, biscuits, cakes with fatty surface', 0, 3),
('03.01', 'Chocolate and chocolate-coated products', 0, 3);

INSERT INTO simulants (name, abbreviation) VALUES
('Ethanol 10% (v/v)', 'A'),
('Acetic acid 3% (w/v)', 'B'),
('Ethanol 20% (v/v)', 'C'),
('Ethanol 50% (v/v)', 'D1'),
('Vegetable oil (<1% unsaponifiable matter)', 'D2'),
('poly(2,6-diphenyl-p-phenylene oxide), 60-80 mesh, 200 nm pores', 'E');

INSERT INTO food_category_simulants (food_category_id, simulant_id) VALUES
(1, 2), (1, 3),
(2, 2), (2, 4),
(3, 3),
(4, 4),
(5, 6),
(6, 5),
(7, 5);

INSERT INTO foods (name, food_category_id) VALUES
('Still water', 1),
('Orange juice with pulp', 2),
('Table wine (12% vol)', 3),
('Whisky', 4),
('Corn starch', 5),
('Butter croissant (surface fat)', 6),
('Chocolate bar', 7);

INSERT INTO substances (smiles, cas_no, fcm_no, ec_ref_no) VALUES
(NULL, '0000087-78-5', 162, 65520),
(NULL, '0000088-24-4', 163, 66400),
(NULL, '0000088-68-6', 164, 34895),
(NULL, '0000088-99-3', 165, 23200),
(NULL, '0000089-32-7', 166, 24057),
(NULL, '0000091-08-7', 167, 25240),
(NULL, '0000091-76-9', 168, 13075),
(NULL, '0000091-97-4', 169, 16240),
(NULL, '0000092-88-6', 170, 16000),
(NULL, '0000093-58-3', 171, 38080),
(NULL, '0000093-89-0', 172, 37840),
(NULL, '0000094-13-3', 173, 60240),
(NULL, '0000095-48-7', 174, 14740);

INSERT INTO sm_entries (substance_id, fcm_no, use_as_additive_or_ppa, use_as_monomer_or_starting_substance, frf_applicable, restrictions_and_specifications) VALUES
(1, 162, 1, 0, 0, NULL),
(2, 163, 1, 0, 1, 'Note (13) applies.'),
(3, 164, 1, 0, 0, 'Only for use in PET for water and beverages.'),
(4, 165, 1, 1, 0, 'Additional ref: 74480.'),
(5, 166, 0, 1, 0, NULL),
(6, 167, 0, 1, 0, '1 mg/kg in final product expressed as isocyanate moiety. Notes (10) apply.'),
(7, 168, 0, 1, 0, 'See ref 15310 (M8).'),
(8, 169, 0, 1, 0, '1 mg/kg in final product expressed as isocyanate moiety. Notes (10) apply.'),
(9, 170, 0, 1, 0, NULL),
(10, 171, 1, 0, 0, NULL),
(11, 172, 1, 0, 0, NULL),
(12, 173, 1, 0, 0, NULL),
(13, 174, 0, 1, 0, NULL);

INSERT INTO sm_entry_limits (sm_entry_id, kind, value, unit_basis) VALUES
(3, 'SML', 0.05, 'FOOD_KG', '0.05'),
(5, 'SML', 0.05, 'FOOD_KG', '0.05'),
(6, 'SML', 1, 'FOOD_KG', '1'),
(7, 'SML', 5, 'FOOD_KG', '5'),
(8, 'SML', 1, 'FOOD_KG', '1'),
(9, 'SML', 6, 'FOOD_KG', '6');

INSERT INTO annex1_group_restrictions (group_restriction_no, total_limit_value, unit_basis, specification) VALUES
(17, 1, 'FOOD_KG', 'Expressed as isocyanate moiety');

INSERT INTO sm_entry_group_restrictions (sm_id, group_restriction_id) VALUES
(6, 1),
(8, 1);
