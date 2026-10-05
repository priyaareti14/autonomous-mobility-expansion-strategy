-- Travel time to work (workers 16+ who did not work from home): universe total
-- Grain: one row per CBSA (metro + micro, July 2023 delineation). Source: RAW.CENSUS_ACS5_2024_CBSA_B08303
{{ acs_cbsa_staging('CENSUS_ACS5_2024_CBSA_B08303', [
        ('B08303_001', 'workers_not_working_from_home')
    ]) }}
