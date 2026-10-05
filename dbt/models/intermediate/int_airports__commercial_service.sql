-- FAA CY2025 commercial-service airports joined to their NASR facility record on the FAA location
-- identifier. That is an objective identifier match: all 516 airports match. The join adds
-- coordinates and the published county name.
-- Grain: one row per commercial-service airport (516).
select
    e.airport_code,
    e.airport_name,
    e.state_usps,
    e.city_published,
    e.service_level_code,
    e.hub_type_code,
    e.hub_type_published,
    e.enplanements_cy2025,
    e.enplanements_cy2024,
    e.enplanement_rank_cy2025,
    n.icao_code,
    n.site_type_code,
    n.latitude,
    n.longitude,
    n.county_name_published,
    n.county_state_usps,
    n.airport_code is not null as has_nasr_record
from {{ ref('stg_faa__enplanements_cy2025') }} e
left join {{ ref('stg_faa__nasr_apt_base') }} n
    on n.airport_code = e.airport_code
