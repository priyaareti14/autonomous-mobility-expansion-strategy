-- Tenure by vehicles available (occupied housing units)
-- Grain: one row per CBSA (metro + micro, July 2023 delineation). Source: RAW.CENSUS_ACS5_2024_CBSA_B25044
{{ acs_cbsa_staging('CENSUS_ACS5_2024_CBSA_B25044', [
        ('B25044_001', 'occupied_units_vehicle_universe'),
        ('B25044_003', 'owner_occupied_no_vehicle'),
        ('B25044_010', 'renter_occupied_no_vehicle')
    ]) }}
