-- c4_unverified_states IS A DETERMINISTIC SET: in FCT_READINESS_BASELINE and the three mode marts
--   * no state appears twice;
--   * states are listed in alphabetical order, separated by ', ';
--   * the list equals the set of states with UNKNOWN_OR_LOW_CONFIDENCE evidence for that market x mode;
--   * it is NULL exactly when C4 is complete (no unverified state), never an empty string.
with b as (
    select market_id, mode, c4_unverified_states, c4_complete_flag from {{ ref('fct_readiness_baseline') }}
),

marts as (
    select 'ROBOTAXI' as mode, market_id, c4_unverified_states from {{ ref('mart_robotaxi_readiness_baseline') }}
    union all
    select 'SIDEWALK_DELIVERY', market_id, c4_unverified_states from {{ ref('mart_sidewalk_delivery_readiness_baseline') }}
    union all
    select 'DRONE_DELIVERY', market_id, c4_unverified_states from {{ ref('mart_drone_delivery_readiness_baseline') }}
),

expected as (
    select market_id, mode, listagg(state_usps, ', ') within group (order by state_usps) as states
    from (
        select distinct market_id, mode, upper(trim(state_usps)) as state_usps
        from {{ ref('int_regulatory__market_state_evidence') }}
        where base_evidence_class = 'UNKNOWN_OR_LOW_CONFIDENCE'
    )
    group by 1, 2
),

items as (
    select b.market_id, b.mode, s.index as pos, s.value::varchar as state_usps
    from b, lateral split_to_table(b.c4_unverified_states, ', ') s
    where b.c4_unverified_states is not null
)

select 'state listed twice' as issue, market_id, mode, state_usps as detail
from items
group by market_id, mode, state_usps
having count(*) > 1

union all
select 'states not in alphabetical order', i1.market_id, i1.mode, i1.state_usps
from items i1
join items i2 on i2.market_id = i1.market_id and i2.mode = i1.mode and i2.pos = i1.pos + 1
where i2.state_usps <= i1.state_usps

union all
select 'list differs from the unverified state set', b.market_id, b.mode, b.c4_unverified_states
from b
left join expected e on e.market_id = b.market_id and e.mode = b.mode
where not equal_null(b.c4_unverified_states, e.states)

union all
select 'NULL / complete mismatch', market_id, mode, c4_unverified_states
from b
where (c4_unverified_states is null) <> c4_complete_flag or c4_unverified_states = ''

union all
select 'mode mart differs from FCT_READINESS_BASELINE', m.market_id, m.mode, m.c4_unverified_states
from marts m
join b on b.market_id = m.market_id and b.mode = m.mode
where not equal_null(m.c4_unverified_states, b.c4_unverified_states)
