-- Median household income in the past 12 months (2024 inflation-adjusted dollars)
-- Grain: one row per CBSA (metro + micro, July 2023 delineation). Source: RAW.CENSUS_ACS5_2024_CBSA_B19013
{{ acs_cbsa_staging('CENSUS_ACS5_2024_CBSA_B19013', [
        ('B19013_001', 'median_household_income_usd')
    ]) }}
