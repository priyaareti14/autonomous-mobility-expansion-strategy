-- FCT_STATION_CLIMATE_NORMALS: annual 1991-2020 climate normals per station (catalogued elements).
-- Grain: one row per station x normals period (one period: 1991-2020), so 15,616 rows.
-- Units as published: inches (precipitation, snowfall), days per year (threshold counts),
-- degrees F (mean temperature).
-- Every element keeps is_published / is_missing / is_trace / comp_flag / years, so missing snow
-- stays distinguishable from zero snow (A-021 open). Snow normals exist at 5,749 stations.
select
    n.* exclude (ingest_run_id, ingested_at, source_id, source_file, source_file_sha256,
                 source_row_number, source_vintage, station_name, latitude, longitude, elevation_m),
    n.source_vintage as normals_vintage
from {{ ref('stg_noaa__normals_annualseasonal') }} n
