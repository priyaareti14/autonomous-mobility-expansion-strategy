-- Households (household type universe)
-- Grain: one row per CBSA (metro + micro, July 2023 delineation). Source: RAW.CENSUS_ACS5_2024_CBSA_B11001
{{ acs_cbsa_staging('CENSUS_ACS5_2024_CBSA_B11001', [
        ('B11001_001', 'total_households')
    ]) }}
