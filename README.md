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
