-- PBI_DIM_MODE: the three autonomous modes. Grain: one row per mode. Scores are never combined across modes.
select 'ROBOTAXI' as mode, 'Robotaxi' as mode_name, 1 as sort_order, 4 as active_component_count,
       false as has_c5_component,
       'Autonomous ride-hailing. C5 Infrastructure & Mode Fit has no approved feature and is structurally absent.' as mode_note
union all
select 'SIDEWALK_DELIVERY', 'Sidewalk delivery robot', 2, 5, true, 'Short-distance, low-speed sidewalk delivery.'
union all
select 'DRONE_DELIVERY', 'Drone delivery', 3, 5, true, 'Small-package aerial delivery. Federal drone rules are context only.'
