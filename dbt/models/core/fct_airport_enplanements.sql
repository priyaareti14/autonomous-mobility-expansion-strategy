-- FCT_AIRPORT_ENPLANEMENTS: FAA CY2025 passenger enplanements at commercial-service airports.
-- Grain: one row per airport x calendar year (CY2025; CY2024 is carried as published), so 516 rows.
-- Unit: enplaned passengers.
-- Not aggregated to markets (A-009 open). Connecting-hub inflation is a known limitation (A-010).
select
    airport_code,
    'CY2025'                            as calendar_year_label,
    service_level_code,
    hub_type_code,
    hub_type_published,
    enplanement_rank_cy2025,
    enplanements_cy2025,
    enplanements_cy2024,
    enplanements_pct_change_published,
    source_vintage                      as faa_vintage
from {{ ref('stg_faa__enplanements_cy2025') }}
