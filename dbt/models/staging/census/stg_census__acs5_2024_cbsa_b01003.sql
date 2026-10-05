-- Total population
-- Grain: one row per CBSA (metro + micro, July 2023 delineation). Source: RAW.CENSUS_ACS5_2024_CBSA_B01003
{{ acs_cbsa_staging('CENSUS_ACS5_2024_CBSA_B01003', [
        ('B01003_001', 'total_population')
    ]) }}
