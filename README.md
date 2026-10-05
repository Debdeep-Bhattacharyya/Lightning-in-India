# Lightning-in-India

## Overview

This repository contains the datasets, source codes, geospatial data, and supporting materials used for research on the **spatiotemporal variability, atmospheric controls, and lightning-related mortality over India**.

The research integrates satellite-based Lightning Imaging Sensor (LIS) observations, atmospheric reanalysis data, National Remote Sensing Centre (NRSC) lightning observations, lightning-fatality records, and GIS datasets.

## Research Focus

The repository supports research on:

- Lightning activity and climatology over India
- Spatial and temporal variability of lightning
- Lightning flash density and lightning activity days
- Lightning hotspots
- Atmospheric controls of lightning activity
- Lightning–atmosphere relationships
- Storm electrical characteristics
- Multi-sensor lightning comparison and validation
- Lightning-related mortality and hazard assessment

## Data

### LIS Data

The repository contains Lightning Imaging Sensor (LIS) observations used for the analysis:

- **TRMM-LIS:** 2000–2014
- **ISS-LIS:** 2018–2022

The TRMM-LIS and ISS-LIS datasets are analysed separately because of differences in their observation characteristics, sampling, and spatial coverage.

The period **2015–2017 represents an observational gap** and is not interpolated or extrapolated.

### Death Data

Lightning-related fatality data are used to investigate the spatial relationship between physical lightning hazard and reported human mortality over India.

### Shapefiles

Geospatial boundary datasets used for spatial analysis, mapping, grid generation, and assignment of lightning observations to administrative and meteorological regions.

## Codes

The `Codes` directory contains the Python and other scripts used for:

- Lightning data preprocessing and quality control
- UTC to IST conversion
- Spatial and temporal processing
- Lightning density calculation
- Grid-based analysis
- Seasonal analysis
- Hotspot analysis
- Atmospheric analysis
- Multi-sensor validation
- Lightning–mortality analysis
- Statistical analysis
- Visualization and figure generation

## Spatial and Temporal Framework

Lightning observations are processed using a common geospatial framework based on **WGS 84 (EPSG:4326)** and a **0.25° × 0.25° analysis grid**.

Lightning observations are assigned to grid cells, States/Union Territories, and IMD homogeneous meteorological divisions.

Observation times are converted from **UTC to Indian Standard Time (IST; UTC + 05:30)** for temporal analysis.

## Atmospheric Data

ERA5 reanalysis data from ECMWF are used to examine atmospheric conditions associated with lightning activity.

The analysis includes thermodynamic, moisture, and dynamical parameters such as:

- CAPE
- CIN
- K Index
- Total Totals Index
- T2M
- T850
- T500
- RH700
- RH850
- TCWV
- TP
- U200
- U850
- V200
- V850

Derived atmospheric indices include:

- Deep Convective Index (DCI)
- Lifted Condensation Level (LCL)
- Showalter Index (SI)
- Deep-layer Wind Shear (WS)

## Repository Structure

```text
Lightning-in-India/
│
├── Codes/
├── Death Data/
├── LIS Data/
├── Shapefiles/
└── README.md
