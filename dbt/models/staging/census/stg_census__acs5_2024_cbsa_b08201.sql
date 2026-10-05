-- Households by vehicles available
-- Grain: one row per CBSA (metro + micro, July 2023 delineation). Source: RAW.CENSUS_ACS5_2024_CBSA_B08201
{{ acs_cbsa_staging('CENSUS_ACS5_2024_CBSA_B08201', [
        ('B08201_001', 'households_vehicle_universe'),
        ('B08201_002', 'households_no_vehicle'),
        ('B08201_003', 'households_1_vehicle'),
        ('B08201_004', 'households_2_vehicles'),
        ('B08201_005', 'households_3_vehicles'),
        ('B08201_006', 'households_4_plus_vehicles')
    ]) }}
