# TES_UE52

**TES_UE52** is a Python-based data analysis framework for processing data acquired from the **Transition Edge Sensor (TES)** at the **UE52-SGM beamline** of **BESSY II**.

The repository provides a complete workflow for converting raw TES detector data into processed Resonant Inelastic X-ray Scattering (RIXS) datasets and extracting spectroscopic information such as Partial Fluorescence Yield (PFY) spectra and RIXS cuts.

The analysis is divided into two sections:

- **Core Analysis Pipeline** – the standard workflow for processing TES data.
- **Additional Analysis Utilities** – optional tools for advanced visualization and specialized analyses.

---

# Core Analysis Pipeline

## 1. Preprocessing

The preprocessing module converts the raw TES detector data and the corresponding beamline metadata into a compact, standardized dataset for RIXS analysis. This significantly reduces the amount of data that needs to be processed in later analysis steps while preserving all relevant experimental information.

### Input

The preprocessing script requires two input datasets for each scan:

- **TES detector data**
  - `date_run_SCAN_scan_xxxx.npz`
  - Contains the timestamp, energy, and detector channel information for every detected photon.

- **Beamline metadata**
  - `date_run_SCAN_scan_xxxx_data/xxxx_beamline_data.npz`
  - Contains the monochromator (incident energy), scan timing, and other beamline parameters required to associate TES events with the corresponding scan point.

### Processing Workflow

For each scan, the script performs the following operations:

1. Loads the TES detector events.
2. Removes detector channels with insufficient statistics.
3. Loads the corresponding beamline data.
4. Matches every TES event to its beamline scan point using timestamps.
5. Constructs the RIXS plane by binning emission energy against incident energy.
6. Saves the processed data together with a quick-look visualization.

### Output

For every processed scan, three files are generated:

| File | Description |
|------|-------------|
| `scanXXXX.npz` | Processed RIXS dataset containing the incident energy grid (`mono`), emission energy grid (`emission`), and 2D intensity map (`counts`). |
| `scanXXXX_bld.npz` | Copy of the beamline metadata used during preprocessing. |
| `scanXXXX.png` | Quick-look visualization of the RIXS plane. |

Example:

```text
scan1587.npz
scan1587_bld.npz
scan1587.png

scan1588.npz
scan1588_bld.npz
scan1588.png
```

The script also generates

```text
processing_log.txt
```

which records the processing status, scan statistics, and any errors encountered during execution.

---

## 2. PFY Processing

The PFY (Partial Fluorescence Yield) processing module extracts PFY spectra from the processed RIXS datasets generated during preprocessing. Multiple scans can be averaged to improve signal quality and reduce statistical noise.

### Input

For each scan:

- `scanXXXX.npz`
- `scanXXXX_bld.npz`

### User Inputs

- Scan range
- Lower emission-energy limit
- Upper emission-energy limit

The selected emission-energy window defines the region used to compute the PFY spectrum.

### Processing Workflow

The script:

1. Loads all selected scans.
2. Integrates the RIXS intensity over the selected emission-energy range.
3. Normalizes each spectrum by the incident beam intensity (`I₀`).
4. Area-normalizes the PFY spectra.
5. Computes the averaged PFY spectrum.
6. Computes the averaged RIXS map.
7. Generates diagnostic plots.

### Output

All processed data are written to

```text
saved_output/
```

containing

```text
avg_emission.txt
avg_mono.txt
avg_rixs_counts.txt

pfy_raw_scanXXXX.txt
pfy_norm_scanXXXX.txt

pfy_norm_average.txt
```

The script also displays

- Averaged RIXS map
- Individual and averaged PFY spectra
- Individual and averaged I₀ curves

---

## 3. RIXS Processing

The RIXS processing module combines multiple scans to generate an averaged RIXS map in energy-loss coordinates and extracts several commonly used one-dimensional cuts.

### Input

Processed RIXS datasets generated during preprocessing:

```text
scanXXXX.npz
```

### User Inputs

- Scan range
- Constant Incident Energy (CIE) cuts
- Constant Charge Transfer (CCT) cuts
- Constant Emission Energy (CEE) cuts

### Processing Workflow

The script

1. Loads all selected scans.
2. Verifies dimensional consistency.
3. Computes the averaged RIXS map.
4. Converts the data to energy-loss coordinates.
5. Saves the averaged dataset as an HDF5 file.
6. Extracts user-defined spectral cuts.
7. Saves every extracted spectrum.

### Output

```text
RIXS_avg_direct_<start>_<end>.h5
```

containing

```text
avg_mono
avg_emission
avg_counts
```

Additional folders are created automatically:

```text
CIE_cuts_<start>_<end>/
CEE_cuts_<start>_<end>/
CCT_cuts_<start>_<end>/
```

Each folder contains the corresponding one-dimensional spectra exported as text files.

The script also produces

- Averaged RIXS energy-loss map
- Constant Incident Energy (CIE) spectra
- Constant Charge Transfer (CCT) spectra
- Constant Emission Energy (CEE) spectra

with the selected cuts overlaid on the RIXS map.

---

# Additional Analysis Utilities

These scripts are optional utilities that provide advanced analysis methods and visualization tools. They are not required for the standard processing pipeline but can be useful for specialized analyses.

---

## Interactive Diagonal PFY Integration

This utility provides an interactive interface for extracting **Diagonal Partial Fluorescence Yield (dPFY)** spectra directly from averaged RIXS maps.

Unlike the standard PFY extraction, which integrates over a fixed emission-energy window, this tool integrates along a user-defined diagonal region of the RIXS plane. The integration region can be modified interactively, allowing rapid exploration of resonant features.

### Features

- Average multiple scans
- Interactive diagonal PFY extraction
- Adjustable diagonal offset
- Adjustable integration width
- Adjustable incident-energy range
- Real-time PFY updates
- Interactive integration-region overlay
- I₀ normalization
- Mouse hover displaying detector counts
- One-click export of the current integration

### Output

The script creates

```text
interactive_diagonal_pfy/
```

containing

```text
diagPFY_offset_*.txt
diagPFY_offset_*_mask.txt
diagPFY_offset_*.png
```

where

| File | Description |
|------|-------------|
| `diagPFY_*.txt` | Normalized diagonal PFY spectrum |
| `*_mask.txt` | Binary integration mask |
| `*.png` | Snapshot of the RIXS map with the selected integration region |

This utility is particularly useful for investigating resonant features that follow diagonal trajectories within the RIXS plane.

---

## Future Utilities

Additional scripts for calibration, visualization, fitting, and advanced analysis will be added here as the repository continues to develop.

---
