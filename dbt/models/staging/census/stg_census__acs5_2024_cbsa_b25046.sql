-- Aggregate number of vehicles available
-- Grain: one row per CBSA (metro + micro, July 2023 delineation). Source: RAW.CENSUS_ACS5_2024_CBSA_B25046
{{ acs_cbsa_staging('CENSUS_ACS5_2024_CBSA_B25046', [
        ('B25046_001', 'aggregate_vehicles_available')
    ]) }}
