-- STATION CLASS CONTRACT: PLCD comes from NOAA HOMR (S-41), not from the GHCN-Daily 'USW' prefix.
-- Known cases verified against HOMR EMSHR 202609 TYPE histories (class as of 2020-12-31):
--   USW00093814 Cincinnati/Northern Kentucky Intl   PLCD
--   USW00023232 Sacramento AP ASOS                  PLCD
--   USW00003017 Denver Intl AP                      PLCD
--   USW00093812 Cincinnati Lunken Field             not PLCD (AIRWAYS, ASOS, COOP)
--   USW00023271 Sacramento 5 ESE                    not PLCD (COOP)
--   USW00023062 Denver-Central Park                 not PLCD (COOP)
--   USW00013988 Kansas City Downtown AP             not PLCD (AIRWAYS, ASOS, COOP)
--   USW00093134 Los Angeles Civic Center            PLCD on 2020-12-31, not PLCD today (class date matters)
with expected as (
    select * from (values
        ('USW00093814', true,  true),  ('USW00023232', true,  true),  ('USW00003017', true, true),
        ('USW00093812', false, false), ('USW00023271', false, false), ('USW00023062', false, false),
        ('USW00013988', false, false), ('USW00093134', true,  false)
    ) as v (station_id, expected_plcd, expected_plcd_current)
)

select e.station_id, e.expected_plcd, c.is_plcd, e.expected_plcd_current, c.is_plcd_current
from expected e
left join {{ ref('int_weather__station_class') }} c on c.station_id = e.station_id
where c.station_id is null
   or c.is_plcd <> e.expected_plcd
   or c.is_plcd_current <> e.expected_plcd_current
   or not c.is_wban_numbered
