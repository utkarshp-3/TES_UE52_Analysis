# TES_UE52

**TES_UE52** is a Python-based data analysis framework for processing data acquired from the **Transition Edge Sensor (TES)** at the **UE52-SGM beamline** of **BESSY II**. The analysis workflow is organized into modular stages to simplify data processing, improve reproducibility, and facilitate future development.

## 1. Preprocessing

The preprocessing module converts the raw TES detector data and the corresponding beamline metadata into a compact, standardized dataset for RIXS analysis. This significantly reduces the amount of data that needs to be processed in later analysis steps while preserving all relevant experimental information.

## Input

The preprocessing script requires two input datasets for each scan:

- **TES detector data**
  - `date_run_SCAN_scan_xxxx.npz`
  - Contains the timestamp, energy, and detector channel information for every detected photon.

- **Beamline metadata**
  - `date_run_SCAN_scan_xxxx_data/xxxx_beamline_data.npz`
  - Contains the monochromator (incident energy), scan timing, and other beamline parameters required to associate TES events with the corresponding scan point.

## Processing Workflow

For each scan, the script performs the following operations:

1. Loads the TES detector events.
2. Removes detector channels with insufficient statistics.
3. Loads the corresponding beamline data.
4. Matches every TES event to its beamline scan point using the acquisition timestamps.
5. Constructs the RIXS plane by binning the emission energy against the incident energy.
6. Saves the processed data together with a quick-look visualization.

## Output

For every processed scan, three files are generated:

| File | Description |
|------|-------------|
| `scanXXXX.npz` | Processed RIXS dataset containing the incident energy grid (`mono`), emission energy grid (`emission`), and 2D intensity map (`counts`). |
| `scanXXXX_bld.npz` | Copy of the beamline metadata used during preprocessing. |
| `scanXXXX.png` | Quick-look visualization of the RIXS plane for rapid inspection of the processed scan. |

Example output:

```
scan1587.npz
scan1587_bld.npz
scan1587.png

scan1588.npz
scan1588_bld.npz
scan1588.png

scan1589.npz
scan1589_bld.npz
scan1589.png
```

In addition, the script generates

```
processing_log.txt
```

which records the processing status, detected files, scan statistics, and any errors encountered during execution.

## Processed Dataset

The generated `scanXXXX.npz` file contains three NumPy arrays:

| Array | Description |
|-------|-------------|
| `mono` | 2D grid of incident (monochromator) energies. |
| `emission` | 2D grid of emission energies. |
| `counts` | 2D histogram (RIXS plane) representing photon counts as a function of incident and emission energy. |

These processed datasets are the primary input for the subsequent analysis modules.


## 2. PFY Processing

The PFY (Partial Fluorescence Yield) processing module extracts PFY spectra from the preprocessed RIXS datasets generated in **Step 1**. Multiple scans can be processed simultaneously, allowing the user to average RIXS maps, compare individual scans, and generate normalized PFY spectra.

### Input

This script operates on the processed output from the preprocessing stage.

For each scan, the following files are required:

- `scanXXXX.npz`
  - Processed RIXS dataset containing:
    - `mono` – incident energy grid
    - `emission` – emission energy grid
    - `counts` – RIXS intensity map

- `scanXXXX_bld.npz`
  - Beamline metadata containing the incident beam intensity (`I0`) and other scan parameters.

### User Inputs

Before processing, the user specifies:

- Scan range (e.g. `1587–1590`)
- PFY integration window:
  - Lower emission energy
  - Upper emission energy

The selected emission energy window defines the region of the RIXS map used to calculate the PFY spectrum.

### Processing Workflow

For every scan, the script performs the following steps:

1. Loads the processed RIXS map.
2. Loads the corresponding beamline metadata.
3. Integrates the RIXS intensity over the selected emission energy window.
4. Normalizes the extracted PFY spectrum by the incident beam intensity (`I0`).
5. Stores the PFY spectrum for each scan.
6. Averages all RIXS maps.
7. Area-normalizes each PFY spectrum.
8. Computes the averaged normalized PFY spectrum.
9. Plots:
   - Average RIXS map
   - Individual and averaged PFY spectra
   - Individual and averaged `I0` curves

### Output

All processed data are saved inside

```text
saved_output/
```

The output directory contains:

| File | Description |
|------|-------------|
| `avg_mono.txt` | Averaged incident energy grid. |
| `avg_emission.txt` | Averaged emission energy grid. |
| `avg_rixs_counts.txt` | Averaged RIXS intensity map. |
| `pfy_raw_scanXXXX.txt` | Raw PFY spectrum extracted from each scan. |
| `pfy_norm_scanXXXX.txt` | Area-normalized PFY spectrum for each scan. |
| `pfy_norm_average.txt` | Averaged normalized PFY spectrum over all processed scans. |

Example output:

```text
saved_output/
│
├── avg_emission.txt
├── avg_mono.txt
├── avg_rixs_counts.txt
├── pfy_norm_average.txt
├── pfy_norm_scan1587.txt
├── pfy_norm_scan1588.txt
├── pfy_norm_scan1589.txt
├── pfy_norm_scan1590.txt
├── pfy_raw_scan1587.txt
├── pfy_raw_scan1588.txt
├── pfy_raw_scan1589.txt
└── pfy_raw_scan1590.txt
```

### Generated Figures

During execution, the script also generates three diagnostic plots:

1. **Average RIXS Map**
   - Averaged two-dimensional RIXS intensity map from all selected scans.

2. **PFY Spectra**
   - Individual normalized PFY spectra.
   - Averaged normalized PFY spectrum.

3. **Incident Beam Intensity (I₀)**
   - Individual I₀ curves for each scan.
   - Averaged I₀ profile.

These plots provide a quick quality check before proceeding with further analysis.


## 3. RIXS Processing

The RIXS processing module combines multiple preprocessed scans to generate an averaged RIXS map in energy-loss coordinates. In addition, it extracts several commonly used one-dimensional cuts from the RIXS plane for detailed spectral analysis.

### Input

The script requires the processed datasets generated during **Step 1**.

For each scan, the following file is required:

- `scanXXXX.npz`
  - Contains:
    - `mono` – incident energy grid
    - `emission` – emission energy grid
    - `counts` – RIXS intensity map

### User Inputs

The user specifies:

- Scan range (e.g. `1587–1590`)
- Incident energies for **Constant Incident Energy (CIE)** cuts
- Energy-loss values for **Constant Charge Transfer (CCT)** cuts
- Emission energies for **Constant Emission Energy (CEE)** cuts

Multiple values may be entered for each cut type.

### Processing Workflow

The script performs the following operations:

1. Loads all selected RIXS datasets.
2. Verifies that all scans have identical dimensions.
3. Averages the RIXS maps over the selected scan range.
4. Converts the data to an energy-loss representation.
5. Saves the averaged dataset as an HDF5 file.
6. Generates an averaged RIXS energy-loss map.
7. Extracts user-defined spectral cuts:
   - Constant Incident Energy (CIE)
   - Constant Charge Transfer (CCT)
   - Constant Emission Energy (CEE)
8. Displays each cut together with its corresponding position on the RIXS map.
9. Saves every extracted cut as an individual text file.

### Output

The averaged RIXS dataset is saved as

```text
RIXS_avg_direct_<start>_<end>.h5
```

which contains

- `avg_mono`
- `avg_emission`
- `avg_counts`

The extracted spectra are organized into dedicated folders:

```text
CIE_cuts_<start>_<end>/
CEE_cuts_<start>_<end>/
CCT_cuts_<start>_<end>/
```

Each folder contains the corresponding one-dimensional spectra exported as text files.

Example directory structure:

```text
Processed/
│
├── RIXS_avg_direct_1587_1590.h5
│
├── CIE_cuts_1587_1590/
│   ├── CIE_Loss_XXXeV.txt
│   └── CIE_Emission_XXXeV.txt
│
├── CEE_cuts_1587_1590/
│   ├── CEE_Incident_XXXeV.txt
│   └── CEE_Loss_XXXeV.txt
│
└── CCT_cuts_1587_1590/
    ├── CCT_Incident_XXXeV.txt
    └── CCT_Emission_XXXeV.txt
```

### Generated Figures

The script produces several diagnostic figures during execution:

1. **Average RIXS Energy-Loss Map**
   - Averaged RIXS intensity displayed in energy-loss coordinates.

2. **Constant Incident Energy (CIE) Cuts**
   - Intensity plotted as a function of:
     - Energy loss
     - Emission energy

3. **Constant Charge Transfer (CCT) Cuts**
   - Intensity plotted as a function of:
     - Incident energy
     - Emission energy

4. **Constant Emission Energy (CEE) Cuts**
   - Intensity plotted as a function of:
     - Incident energy
     - Energy loss

The selected cut positions are overlaid on the RIXS map, providing a visual reference for the extracted spectra.

### Available Cut Types

| Cut | Description |
|------|-------------|
| **CIE (Constant Incident Energy)** | Extracts spectra at fixed incident energy, allowing analysis of emission features and energy-loss excitations. |
| **CCT (Constant Charge Transfer)** | Extracts spectra along constant energy-loss values, useful for following the evolution of specific excitations with incident energy. |
| **CEE (Constant Emission Energy)** | Extracts spectra at fixed emission energy to investigate resonant behavior across the incident energy axis. |
