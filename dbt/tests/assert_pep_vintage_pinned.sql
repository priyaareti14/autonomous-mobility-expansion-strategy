-- CONTRACT: the market universe comes from the pinned PEP snapshot: Vintage 2025, with the
-- SHA-256 recorded in Phase 1 (project_scope.md section 5). A different file would mean the
-- frozen universe was rebuilt from unapproved data.
select market_id, pep_vintage, pep_file_sha256
from {{ ref('dim_market') }}
where pep_vintage <> 'V2025'
   or pep_file_sha256 <> 'BF6FAD83753456413D047D1ACEBEB434BD067EBA9D6D0BE62B3F737AD1301852'
