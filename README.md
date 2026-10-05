Lightning-in-India    [![DOI](https://zenodo.org/badge/1405217695.svg)](https://doi.org/10.5281/zenodo.23158026)


Overview
This repository contains the research datasets, source codes, geospatial resources, and supporting materials used for research on the spatiotemporal variability, atmospheric controls, storm characteristics, and lightning-related mortality over India. The research integrates satellite-based Lightning Imaging Sensor (LIS) observations, atmospheric reanalysis data, National Remote Sensing Centre (NRSC) lightning observations, lightning-fatality statistics, and geospatial datasets within a common GIS and statistical analysis framework.  The repository is intended to support research transparency, reproducibility, methodological documentation, and responsible reuse of the associated code and research materials.

Research Focus
The research supported by this repository addresses the following themes:
- Lightning climatology over India
- Spatial and temporal variability of lightning activity
- Lightning flash density
- Lightning activity days
- Lightning hotspots and spatial concentration
- Seasonal and diurnal variability of lightning
- Atmospheric controls of lightning activity
- Lightning–atmosphere relationships
- Thermodynamic, moisture, and dynamical controls
- Storm electrical characteristics
- Multi-sensor lightning comparison and validation
- Lightning hazard assessment
- Lightning-related mortality and reported fatality patterns
- Relationships between physical lightning hazard and human mortality

Data
1. Lightning Imaging Sensor (LIS) Data
The repository contains LIS-based lightning observations used in the
analysis:
- TRMM-LIS: 2000–2014
- ISS-LIS: 2018–2022
The two LIS missions are analysed separately because they differ in orbital configuration, observation characteristics, spatial sampling, coverage, and detection/sampling conditions.
The period 2015–2017 represents an observational gap between the TRMM-LIS and ISS-LIS datasets. This gap is not interpolated or extrapolated.
LIS observations represent total lightning, including both cloud-to-ground and intra-cloud lightning, as detected by the Lightning Imaging Sensor.

Original Data Source
The LIS datasets were obtained from the NASA Global Hydrometeorology Resource Center (GHRC) DAAC.
Original data providers and dataset documentation should be cited whenever the LIS data are reused.

TRMM-LIS data access: https://lightning.nsstc.nasa.gov/nlisib/lissearch.pl?origin=ST&lat=21&lon=85&alat=10&alon=10&donob=both
ISS-LIS data access: https://lightning.nsstc.nasa.gov/isslisib/lissearch.pl?coords=?521,131

Users should consult the original NASA/GHRC documentation and applicable
data-use conditions before redistributing the original files.

2. Lightning Fatality / Death Data
Lightning-related fatality statistics are used to investigate the spatial relationship between physical lightning hazard and reported human
mortality over India. The mortality component is based on statistics and publications of the National Crime Records Bureau (NCRB), Ministry of Home Affairs, Government of India.

Original source:
https://www.ncrb.gov.in/accidental-deaths-suicides-in-india-adsi.html

Where datasets in this repository have been compiled, extracted, transcribed, harmonized, or otherwise derived from published NCRB statistics, they should be regarded as researcher-compiled or
researcher-derived datasets and not as official NCRB datasets. Users should consult the original NCRB publication/source and applicable terms or permissions before redistributing the original NCRB material.

3. ERA5 Reanalysis Data
ERA5 atmospheric reanalysis data are used to investigate environmental conditions associated with lightning activity.
The ERA5 dataset is provided by the European Centre for Medium-Range Weather Forecasts (ECMWF) through the Copernicus Climate Change Service / Climate Data Store.

Original data source:
https://cds.climate.copernicus.eu/datasets

The atmospheric analysis includes thermodynamic, moisture, and dynamical
variables relevant to deep convection and lightning development.

4. NRSC Lightning Observations
Lightning observations from the National Remote Sensing Centre (NRSC), Indian Space Research Organisation (ISRO) are used where applicable for lightning-event analysis, spatial validation, and comparison with
satellite-based observations. The NRSC observations are treated as an independent lightning observation source in analyses where multi-sensor comparison or validation is required. The availability, redistribution, and use of NRSC data are subject to the terms under which the data were obtained.

5. Shapefiles and Geospatial Data
The repository contains geospatial boundary datasets used for:
- Spatial analysis
- Cartographic visualization
- Grid generation
- Spatial aggregation
- Administrative assignment
- Meteorological-region assignment
- Lightning hotspot mapping
- Lightning–mortality spatial analysis
Where third-party shapefiles or boundary datasets are used, the original source and applicable licence or attribution requirements should be retained.

Observation Period and Sensor Strategy
The primary satellite lightning analysis covers:
Dataset	  Observation   Period  	Source
TRMM-LIS	2000–2014	     NASA       GHRC
ISS-LIS	  2018–2022	     NASA       GHRC
Observational gap	2015–2017	No LIS interpolation/extrapolation


TRMM-LIS and ISS-LIS are therefore treated as separate observational periods rather than being merged into a single continuous sensor record. Comparisons between the two LIS datasets focus on relative spatial,
seasonal, and temporal characteristics while accounting for differences in observation and sampling conditions.

Spatial and Temporal Framework
Coordinate Reference System
The analysis uses:
- Coordinate Reference System: WGS 84
- EPSG: 4326
- Geographic coordinates: Longitude/Latitude

Analysis Grid
A 0.25° × 0.25° geographic analysis grid is used for spatial aggregation and comparison of lightning observations. Lightning observations are spatially assigned to the analysis grid and, where required, to:
- States
- Union Territories
- IMD homogeneous meteorological divisions
- Other administrative or geographic units

Time Standard
Original lightning observation times are handled in UTC. For temporal and diurnal analysis, observation times are converted to: Indian Standard Time (IST) = UTC + 05:30 The UTC-to-IST conversion is implemented programmatically in the analysis workflow.

Atmospheric Data and Variables
ERA5 reanalysis data are used to characterize the atmospheric environment associated with lightning occurrence and intensity.

Thermodynamic and Moisture Variables
The analysis includes parameters such as:
- CAPE — Convective Available Potential Energy
- CIN — Convective Inhibition
- K Index
- Total Totals Index
- T2M — 2-metre air temperature
- T850 — Temperature at 850 hPa
- T500 — Temperature at 500 hPa
- RH700 — Relative humidity at 700 hPa
- RH850 — Relative humidity at 850 hPa
- TCWV — Total column water vapour
- TP — Total precipitation

Dynamical Variables
The analysis includes:
- U200 — Zonal wind at 200 hPa
- U850 — Zonal wind at 850 hPa
- V200 — Meridional wind at 200 hPa
- V850 — Meridional wind at 850 hPa
Additional pressure-level and surface variables may be included depending on the specific analysis or experiment.

Derived Atmospheric Indices
Derived indicators include:
- Deep Convective Index (DCI)
- Lifted Condensation Level (LCL)
- Showalter Index (SI)
- Deep-layer Wind Shear (WS)
The exact mathematical formulation of each derived index should be specified in the corresponding analysis code or methodological documentation.

Analysis and Processing Workflow
The Codes/ directory contains scripts used for data preparation, analysis, statistical evaluation, and visualization.

Major processing components include:
1. Data ingestion and organization
2. Lightning data preprocessing
3. Quality control and filtering
4. UTC-to-IST conversion
5. Spatial coordinate processing
6. Grid generation and spatial aggregation
7. State/UT and IMD division assignment
8. Temporal and seasonal classification
9. Lightning flash-density calculation
10. Lightning activity-day analysis
11. Hotspot and spatial-pattern analysis
12. Atmospheric-variable extraction and matching
13. Lightning–atmosphere analysis
14. Multi-sensor comparison and validation
15. Lightning–mortality analysis
16. Statistical analysis
17. Figure and map generation
The repository may contain scripts corresponding to individual analyses,
experiments, preprocessing stages, and visualization workflows.

Research Seasons
The analysis follows the seasonal framework used for the India-wide lightning study:
Season	                    Months
Winter	                January–February
Pre-monsoon	            March–May
Southwest Monsoon	      June–September
Post-monsoon	          October–December


Seasonal classifications are applied consistently across relevant  lightning and atmospheric analyses. Multi-Sensor Comparison and Validation  Where TRMM-LIS, ISS-LIS, and NRSC lightning observations are compared,  the analysis accounts for differences in sensor characteristics and  sampling.

Depending on the analysis, comparison procedures may include:
- Spatial correspondence
- Temporal correspondence
- Correlation analysis
- Pearson correlation
- Spearman rank correlation
- Bias assessment
- RMSE
- Log-transformed comparison
- Spatial consistency assessment
The TRMM-LIS and ISS-LIS datasets are not assumed to be directly
equivalent in absolute flash magnitude.

Repository Structure
Lightning-in-India/
│
├── Codes/
│   ├── Data preprocessing/
│   ├── Spatial analysis/
│   ├── Temporal analysis/
│   ├── Atmospheric analysis/
│   ├── Validation/
│   ├── Mortality analysis/
│   └── Visualization/
│
├── Death Data/
│
├── LIS Data/
│
├── Shapefiles/
│
└── README.md

The exact contents and subdirectory structure may evolve as additional research analyses and reproducibility materials are added. Software and Computational Tools
The analysis uses Python-based scientific and geospatial workflows, together with GIS software.

Programming Language
- Python
GIS and Geospatial Software
- QGIS
- ArcGIS

Python Libraries
Depending on the specific analysis, the repository uses libraries
including:
- NumPy
- pandas
- GeoPandas
- Xarray
- SciPy
- Matplotlib
- Seaborn
- Rasterio
- Shapely
- scikit-learn
Additional packages may be required for individual scripts. The required
packages should be documented in the relevant script or environment file
when applicable.

Reproducibility
The repository is designed to support reproducible research by providing:
- Analysis scripts
- Data-processing workflows
- Spatial-analysis procedures
- Statistical-analysis procedures
- Visualization scripts
- Research datasets or derived datasets where permitted
- Documentation of data sources
- Description of coordinate and temporal frameworks

Because several datasets are provided by external organizations, complete reproduction may require downloading the original datasets directly from their respective providers. Users should preserve the original data-provider metadata and citations when reproducing the analyses.

Data Availability and Redistribution
This repository combines original research code with datasets obtained from external data providers.

Important
Not all files in this repository necessarily have the same redistribution conditions.

In particular:
- NASA/GHRC LIS data remain associated with NASA/GHRC and the original
  dataset documentation.
- ERA5 data remain subject to the applicable Copernicus/ECMWF data terms.
- NRSC/ISRO data remain subject to the conditions under which the data
  were obtained.
- NCRB statistics remain attributable to NCRB and the original
  Government of India publications.
- Third-party shapefiles remain subject to their original source and
  licence conditions.
- Researcher-generated code and derived products should be distinguished
  clearly from original third-party datasets.
Users should verify the applicable terms of the original data source before redistributing third-party data.

Citation
If you use the code, derived datasets, analytical methods, or research materials from this repository, please cite this repository and the associated research publication(s), where applicable.

Dataset Attribution
- NASA Global Hydrometeorology Resource Center (GHRC) DAAC — LIS
- European Centre for Medium-Range Weather Forecasts (ECMWF) /
  Copernicus Climate Change Service — ERA5
- National Remote Sensing Centre (NRSC), ISRO — lightning observations
- National Crime Records Bureau (NCRB), Ministry of Home Affairs,
  Government of India — fatality statistics

Research Publications
This repository supports research on lightning climatology, atmospheric controls, storm characteristics, and lightning-related mortality over India.
Publication details and DOI links will be added here as the associated research outputs are published.

Data Use and Responsible Reuse
Users are encouraged to use the repository for legitimate scientific, educational, and research purposes while maintaining appropriate attribution.

When reusing data:
1. Cite the original data provider.
2. Cite this repository when using its code or derived research products.
3. Preserve relevant metadata.
4. Do not represent third-party datasets as original datasets produced by
   this repository.
5. Clearly distinguish researcher-derived products from official
   government or satellite datasets.
6. Check the applicable terms of the original data provider before
   redistributing third-party files.

License
The repository contains a mixture of researcher-developed code, derived research products, and third-party datasets.
Therefore, a single blanket licence should not be assumed to apply to all contents of the repository.
Unless otherwise specified in an individual file or directory:
- Researcher-developed code is provided for research and reproducibility
  purposes.
- Third-party datasets remain subject to their original provider's
  terms, conditions, licences, and attribution requirements.
- Users should consult the relevant source documentation before
  redistributing third-party datasets.
A repository-level software licence may be added separately for the researcher-developed code.

Acknowledgements
The research acknowledges the organizations that provide the datasets and infrastructure used in this work, including:
- NASA Global Hydrometeorology Resource Center (GHRC) DAAC
- National Aeronautics and Space Administration (NASA)
- European Centre for Medium-Range Weather Forecasts (ECMWF)
- Copernicus Climate Change Service
- National Remote Sensing Centre (NRSC)
- Indian Space Research Organisation (ISRO)
- National Crime Records Bureau (NCRB)
- Ministry of Home Affairs, Government of India

Contact
For questions regarding the research methodology, code, derived datasets, or scientific use of this repository, please contact the repository authors through the associated GitHub repository or research publication.

Disclaimer
This repository is intended for scientific research and reproducibility. The analyses, derived datasets, interpretations, and visualizations provided in this repository are the responsibility of the researchers and should not be interpreted as official products of NASA, GHRC, ECMWF, Copernicus, NRSC, ISRO, NCRB, or the Government of India unless explicitly stated.

Third-party datasets remain the property and responsibility of their respective data providers.

Repository Status
Status: Active Research Repository
The repository is being progressively updated as additional analysis
scripts, derived datasets, documentation, and research outputs are
finalized.
