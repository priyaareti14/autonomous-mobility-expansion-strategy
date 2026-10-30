# Notice: third-party data and sources

The [MIT License](LICENSE) covers only the **original code and documentation** in this repository. It does not cover third-party data or content.

## Third-party datasets

The analysis uses public datasets that **remain subject to their providers' own licenses, terms of use and citation requirements**:

- U.S. Census Bureau: Population Estimates Program, American Community Survey, County Business Patterns, CBSA delineation files, Gazetteer files, Census Geocoder;
- U.S. Bureau of Labor Statistics: Occupational Employment and Wage Statistics;
- NOAA National Centers for Environmental Information: U.S. Climate Normals and the Historical Observing Metadata Repository;
- Federal Aviation Administration: passenger boarding (enplanement) data and NASR airport data;
- U.S. Environmental Protection Agency: Smart Location Database.

Raw source files are **not** redistributed in this repository. The ingestion code downloads them from the official URLs listed in `config/ingestion_sources.json`. Derived outputs in `outputs/` are analytical results computed from these sources.

## Curated evidence

`evidence/regulatory_evidence.csv` and `evidence/deployment_evidence.csv` are analyst-curated summaries with citations to state legislatures, state and federal agencies, operator and platform publications, and news or reference sites. The cited works remain the property of their respective owners. The regulatory classification is analytical and **is not legal advice**.

## Trademarks and affiliation

Company and product names mentioned (for example in deployment evidence or the disclaimer) are trademarks of their respective owners and are used only to identify publicly reported activity. This is an independent portfolio project, not affiliated with or endorsed by any company named.
