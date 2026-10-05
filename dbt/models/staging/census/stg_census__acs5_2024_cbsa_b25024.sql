-- Units in structure (housing units)
-- Grain: one row per CBSA (metro + micro, July 2023 delineation). Source: RAW.CENSUS_ACS5_2024_CBSA_B25024
{{ acs_cbsa_staging('CENSUS_ACS5_2024_CBSA_B25024', [
        ('B25024_001', 'housing_units_total'),
        ('B25024_002', 'housing_units_1_detached'),
        ('B25024_003', 'housing_units_1_attached'),
        ('B25024_004', 'housing_units_2'),
        ('B25024_005', 'housing_units_3_or_4'),
        ('B25024_006', 'housing_units_5_to_9'),
        ('B25024_007', 'housing_units_10_to_19'),
        ('B25024_008', 'housing_units_20_to_49'),
        ('B25024_009', 'housing_units_50_plus'),
        ('B25024_010', 'housing_units_mobile_home'),
        ('B25024_011', 'housing_units_boat_rv_van')
    ]) }}
