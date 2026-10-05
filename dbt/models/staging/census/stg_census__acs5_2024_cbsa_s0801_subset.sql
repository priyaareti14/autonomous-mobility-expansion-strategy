-- Subject table S0801: mean travel time to work in minutes (workers 16+ who did not work from home)
-- Grain: one row per CBSA (metro + micro, July 2023 delineation). Source: RAW.CENSUS_ACS5_2024_CBSA_S0801_SUBSET
{{ acs_cbsa_staging('CENSUS_ACS5_2024_CBSA_S0801_SUBSET', [
        ('S0801_C01_046', 'mean_travel_time_minutes')
    ]) }}
