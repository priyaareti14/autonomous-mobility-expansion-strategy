-- LABOR-COST CANDIDATES (Phase 5 decision A-026): BLS OEWS May 2025 annual median wages.
-- Grain: one row per market (35).
--   53-3053 Shuttle Drivers and Chauffeurs -> robotaxi cost of the human alternative.
--     SOC 2018 / O*NET: "Drive a motor vehicle to transport passengers on a planned or scheduled
--     basis. May collect a fare. Includes nonemergency medical transporters and hearse drivers."
--   43-5021 Couriers and Messengers -> sidewalk-robot and drone cost of the human alternative.
--     SOC 2018 / O*NET: "Pick up and deliver messages, documents, packages, and other items between
--     offices or departments within an establishment or directly to other business concerns,
--     traveling by foot, bicycle, motorcycle, automobile, or public conveyance."
-- 53-3054 Taxi Drivers is NOT carried: published for 7 of 35 markets, DROPPED (TOO_MISSING), never imputed.
-- OEWS excludes the self-employed, so app-based gig drivers and couriers are largely absent (A-017).
-- BLS markers (* not available, # top-coded) are carried; a marker means the value is not usable.
with w as (
    select * from {{ ref('fct_market_occupation_wages') }}
    where occupation_code in ('53-3053', '43-5021')
)

select
    d.market_id,
    max(iff(w.occupation_code = '53-3053', w.annual_median_wage_usd, null))        as shuttle_chauffeur_median_annual_wage_usd,
    max(iff(w.occupation_code = '53-3053', w.annual_median_wage_usd_marker, null)) as shuttle_chauffeur_wage_marker,
    max(iff(w.occupation_code = '53-3053', w.occupation_title, null))              as shuttle_chauffeur_occupation_title,
    max(iff(w.occupation_code = '43-5021', w.annual_median_wage_usd, null))        as courier_median_annual_wage_usd,
    max(iff(w.occupation_code = '43-5021', w.annual_median_wage_usd_marker, null)) as courier_wage_marker,
    max(iff(w.occupation_code = '43-5021', w.occupation_title, null))              as courier_occupation_title,
    'May2025'                                                                       as oews_vintage
from {{ ref('dim_market') }} d
left join w on w.market_id = d.market_id
group by d.market_id
