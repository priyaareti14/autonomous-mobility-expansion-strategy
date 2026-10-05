-- Tenure (occupied housing units)
-- Grain: one row per CBSA (metro + micro, July 2023 delineation). Source: RAW.CENSUS_ACS5_2024_CBSA_B25003
{{ acs_cbsa_staging('CENSUS_ACS5_2024_CBSA_B25003', [
        ('B25003_001', 'occupied_housing_units'),
        ('B25003_002', 'owner_occupied_units'),
        ('B25003_003', 'renter_occupied_units')
    ]) }}
