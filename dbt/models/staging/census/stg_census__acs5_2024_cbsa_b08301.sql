-- Means of transportation to work, workers 16+
-- Grain: one row per CBSA (metro + micro, July 2023 delineation). Source: RAW.CENSUS_ACS5_2024_CBSA_B08301
{{ acs_cbsa_staging('CENSUS_ACS5_2024_CBSA_B08301', [
        ('B08301_001', 'workers_16_plus'),
        ('B08301_003', 'workers_drove_alone'),
        ('B08301_010', 'workers_public_transportation'),
        ('B08301_016', 'workers_taxi_or_ride_hailing'),
        ('B08301_018', 'workers_bicycle'),
        ('B08301_019', 'workers_walked'),
        ('B08301_021', 'workers_worked_from_home')
    ]) }}
