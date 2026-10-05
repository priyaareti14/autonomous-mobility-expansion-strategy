-- S-17 FAA CY2025 commercial-service enplanements.
-- Grain: one row per airport (516; the sheet's 6 summary rows were rejected at ingestion, see META).
-- hub_type_code: L/M/S/N for primary airports. The source writes the text 'None' for nonprimary
-- commercial-service airports; that becomes null, and the original stays in hub_type_published.
select
    {{ clean_text('"LOCID"') }}                                  as airport_code,
    {{ to_integer('"RANK"') }}                                   as enplanement_rank_cy2025,
    {{ clean_text('"RO"') }}                                     as faa_region_code,
    {{ clean_text('"ST"') }}                                     as state_usps,
    {{ clean_text('"CITY"') }}                                   as city_published,
    {{ clean_text('"AIRPORT_NAME"') }}                           as airport_name,
    {{ clean_text('"S_L"') }}                                    as service_level_code,
    nullif({{ clean_text('"HUB"') }}, 'None')                    as hub_type_code,
    {{ clean_text('"HUB"') }}                                    as hub_type_published,
    {{ to_integer('"CY_25_ENPLANEMENTS"') }}                     as enplanements_cy2025,
    {{ to_integer('"CY_24_ENPLANEMENTS"') }}                     as enplanements_cy2024,
    {{ to_number('"PCT_CHANGE"') }}                              as enplanements_pct_change_published,
    'CY2025'                                                     as calendar_year_label,
    {{ lineage_columns() }}
from {{ source('raw', 'FAA_ENPLANEMENTS_CY2025_COMMERCIAL_SERVICE') }}
