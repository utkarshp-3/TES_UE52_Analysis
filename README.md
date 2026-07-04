# TES_UE52

**TES_UE52** is a Python-based data analysis framework for processing data acquired from the **Transition Edge Sensor (TES)** at the **UE52-SGM beamline** of **BESSY II**. The analysis workflow is organized into modular stages to simplify data processing, improve reproducibility, and facilitate future development.

## 1. Preprocessing

The preprocessing stage combines and organizes the raw detector data with the corresponding beamline metadata into a unified dataset suitable for subsequent analysis.

### Input Files

The preprocessing script requires the following input files:

- Beamline data file (typically named `date_run_SCAN_scan_xxxx_data`)
- Corresponding TES detector data file (`date_run_SCAN_scan_xxxx.npz`)

### Processing Steps

The preprocessing routine performs the following tasks:

- Loads the detector and beamline datasets.
- Synchronizes and merges the relevant information into a single RIXS plane dataset.
- Extracts only the data required for subsequent analysis, reducing the dataset size and improving processing efficiency.
- Saves the processed dataset to a dedicated output directory.

### Output

The output of the preprocessing stage is a standardized and compact RIXS dataset that serves as the input for the subsequent analysis pipeline. By consolidating the raw detector and beamline data into an easily accessible format, the preprocessing step significantly simplifies downstream analysis and reduces computational overhead.
