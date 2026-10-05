-- Aggregate travel time to work in minutes (workers 16+ who did not work from home)
-- Grain: one row per CBSA (metro + micro, July 2023 delineation). Source: RAW.CENSUS_ACS5_2024_CBSA_B08013
{{ acs_cbsa_staging('CENSUS_ACS5_2024_CBSA_B08013', [
        ('B08013_001', 'aggregate_travel_time_minutes')
    ]) }}
