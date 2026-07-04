#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun  3 08:50:46 2026

@author: utkarshprakash
"""

import os
import re
import shutil
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

# ============================================================
# USER SETTINGS
# ============================================================

RAW_DATA_DIR ='/Users/utkarshprakash/Documents/Phd/Beamtime/Data/TES Beamtime/Novemeber/Analysis/Analysis/Ferrocynide/Raw_Data'

OUTPUT_DIR = '/Users/utkarshprakash/Documents/Phd/Beamtime/Data/TES Beamtime/Novemeber/Analysis/Analysis/Ferrocynide/Testing_newcode'

# ============================================================
# RIXS SETTINGS
# ============================================================

EMISSION_MIN = 200.0
EMISSION_MAX = 1000.0
EMISSION_BIN = 0.1

MIN_COUNTS_PER_CHANNEL = 50

# ============================================================
# CREATE OUTPUT FOLDER
# ============================================================

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)

# ============================================================
# LOGGING
# ============================================================

LOGFILE = os.path.join(
    OUTPUT_DIR,
    "processing_log.txt"
)

with open(LOGFILE, "w") as f:
    f.write("TES RIXS PROCESSING LOG\n")
    f.write("=" * 80 + "\n\n")


def log(message):

    print(message)

    with open(LOGFILE, "a") as f:
        f.write(message + "\n")


# ============================================================
# PARSE SCANS
# ============================================================

def parse_scans(scan_text):

    scan_text = scan_text.strip().lower()

    # --------------------------------------------------------
    # ALL SCANS
    # --------------------------------------------------------

    if scan_text == "all":

        scans = []

        for fname in os.listdir(RAW_DATA_DIR):

            if (
                fname.endswith(".npz")
                and "beamline" not in fname
            ):

                m = re.search(
                    r"scan_(\d+)",
                    fname,
                    re.IGNORECASE
                )

                if m:

                    scans.append(
                        int(m.group(1))
                    )

        scans = sorted(
            list(set(scans))
        )

        return scans

    # --------------------------------------------------------
    # RANGE
    # --------------------------------------------------------

    if "-" in scan_text:

        start, stop = map(
            int,
            scan_text.split("-")
        )

        return list(
            range(
                start,
                stop + 1
            )
        )

    # --------------------------------------------------------
    # LIST
    # --------------------------------------------------------

    return [
        int(x.strip())
        for x in scan_text.split(",")
        if x.strip()
    ]


# ============================================================
# FIND FILES
# ============================================================

def find_scan_files(scan_number):

    scan_tag = f"scan_{scan_number}"

    tes_file = None
    beamline_file = None

    for fname in os.listdir(RAW_DATA_DIR):

        if (
            fname.endswith(".npz")
            and scan_tag in fname
            and "beamline" not in fname
        ):

            tes_file = os.path.join(
                RAW_DATA_DIR,
                fname
            )

            break

    if tes_file is None:

        return None, None

    stem = Path(tes_file).stem

    beamline_dir = os.path.join(
        RAW_DATA_DIR,
        stem + "_data"
    )

    if not os.path.isdir(
        beamline_dir
    ):

        return tes_file, None

    for fname in os.listdir(
        beamline_dir
    ):

        if fname.endswith(
            "_beamline_data.npz"
        ):

            beamline_file = os.path.join(
                beamline_dir,
                fname
            )

            break

    return tes_file, beamline_file


# ============================================================
# PROCESS SCAN
# ============================================================

def process_scan(scan_number):

    log("")
    log("=" * 80)
    log(
        f"PROCESSING SCAN {scan_number}"
    )
    log("=" * 80)

    tes_file, beamline_file = (
        find_scan_files(
            scan_number
        )
    )

    if tes_file is None:

        raise FileNotFoundError(
            f"TES file not found "
            f"for scan {scan_number}"
        )

    if beamline_file is None:

        raise FileNotFoundError(
            f"Beamline file not found "
            f"for scan {scan_number}"
        )

    log(
        f"TES FILE:\n{tes_file}"
    )

    log("")

    log(
        f"BEAMLINE FILE:\n"
        f"{beamline_file}"
    )

    # ========================================================
    # LOAD TES
    # ========================================================

    log("")
    log("Loading TES data...")

    tes = np.load(
        tes_file
    )

    timestamps = tes[
        "timestamps"
    ]

    energies = tes[
        "energies"
    ]

    channels = tes[
        "channels"
    ]

    log(
        f"TES events: "
        f"{len(energies):,}"
    )

    event_time = (
        timestamps / 1e9
    )

    unique_ch, ch_counts = (
        np.unique(
            channels,
            return_counts=True
        )
    )

    good_channels = unique_ch[
        ch_counts >=
        MIN_COUNTS_PER_CHANNEL
    ]

    channel_mask = np.isin(
        channels,
        good_channels
    )

    event_time = event_time[
        channel_mask
    ]

    energies = energies[
        channel_mask
    ]

    log(
        f"Using "
        f"{len(good_channels)} "
        f"channels"
    )

    # ========================================================
    # LOAD BEAMLINE
    # ========================================================

    log("")
    log(
        "Loading beamline data..."
    )

    beam = np.load(
        beamline_file
    )

    incident_energy = beam[
        "sgm_en"
    ]

    scan_start = beam[
        "tes_scan_point_start"
    ]

    scan_end = beam[
        "tes_scan_point_end"
    ]

    log(
        f"Scan points: "
        f"{len(incident_energy)}"
    )

    # ========================================================
    # MATCH EVENTS
    # ========================================================

    log("")
    log(
        "Matching TES events..."
    )

    idx = np.searchsorted(
        scan_start,
        event_time,
        side="right"
    ) - 1

    valid = (
        (idx >= 0)
        &
        (idx < len(scan_start))
    )

    idx_valid = idx[valid]

    inside_window = (
        event_time[valid]
        <= scan_end[idx_valid]
    )

    valid_indices = (
        np.where(valid)[0]
        [inside_window]
    )

    idx = idx[
        valid_indices
    ]

    event_eout = energies[
        valid_indices
    ]

    event_ein = incident_energy[
        idx
    ]

    log(
        f"Matched events: "
        f"{len(event_eout):,}"
    )

    # ========================================================
    # BUILD RIXS PLANE
    # ========================================================

    log("")
    log(
        "Building RIXS plane..."
    )

    eout_edges = np.arange(
        EMISSION_MIN,
        EMISSION_MAX +
        EMISSION_BIN,
        EMISSION_BIN
    )

    if len(
        incident_energy
    ) > 1:

        dE = np.median(
            np.diff(
                incident_energy
            )
        )

    else:

        dE = 0.1

    ein_edges = np.concatenate(
        [
            incident_energy
            - dE / 2,
            [
                incident_energy[-1]
                + dE / 2
            ]
        ]
    )

    rixs_plane, _, _ = (
        np.histogram2d(
            event_ein,
            event_eout,
            bins=[
                ein_edges,
                eout_edges
            ]
        )
    )

    # ========================================================
    # SAVE RIXS
    # ========================================================

    rixs_file = os.path.join(
        OUTPUT_DIR,
        f"scan{scan_number}.npz"
    )
    # Build 2D grids exactly like old format
    
    mono_grid, emission_grid = np.meshgrid(
        incident_energy,
        eout_edges[:-1]
    )
    
    np.savez(
        rixs_file,
        mono=mono_grid,
        emission=emission_grid,
        counts=rixs_plane.T
    )
    # ========================================================
    # SAVE BEAMLINE
    # ========================================================

    beamline_out = os.path.join(
        OUTPUT_DIR,
        f"scan{scan_number}_bld.npz"
    )

    shutil.copy2(
        beamline_file,
        beamline_out
    )

    # ========================================================
    # SAVE FIGURE
    # ========================================================

    png_file = os.path.join(
        OUTPUT_DIR,
        f"scan{scan_number}.png"
    )

    plt.figure(
        figsize=(8, 6)
    )

    extent = [
        ein_edges[0],
        ein_edges[-1],
        eout_edges[0],
        eout_edges[-1]
    ]

    plt.imshow(
        rixs_plane.T,
        origin="lower",
        aspect="auto",
        extent=extent,
        interpolation="nearest"
    )

    plt.xlabel(
        "Incident Energy (eV)"
    )

    plt.ylabel(
        "Emission Energy (eV)"
    )

    plt.title(
        f"Scan {scan_number}"
    )

    plt.colorbar(
        label="Counts"
    )

    plt.tight_layout()

    plt.savefig(
        png_file,
        dpi=300
    )

    plt.close()

    # ========================================================
    # VERIFY FILES
    # ========================================================

    log("")
    log("Verifying outputs...")

    for outfile in [
        rixs_file,
        beamline_out,
        png_file
    ]:

        if os.path.exists(
            outfile
        ):

            size_mb = (
                os.path.getsize(
                    outfile
                )
                / 1024**2
            )

            log(
                f"✓ SAVED: "
                f"{outfile}"
            )

            log(
                f"  Size: "
                f"{size_mb:.2f} MB"
            )

        else:

            raise RuntimeError(
                f"Output missing:\n"
                f"{outfile}"
            )

    log("")
    log(
        f"SCAN {scan_number} "
        f"COMPLETE"
    )


# ============================================================
# MAIN
# ============================================================

print()
print("=" * 80)
print("TES RIXS BATCH PROCESSOR")
print("=" * 80)

scan_text = input(
    "\nEnter scans "
    "(1312-1316, "
    "1312,1314,1315, "
    "or all):\n\n"
)

SCANS = parse_scans(
    scan_text
)

log("")
log("=" * 80)
log("RUN STARTED")
log("=" * 80)

log(
    f"RAW DATA DIRECTORY:\n"
    f"{RAW_DATA_DIR}"
)

log("")

log(
    f"OUTPUT DIRECTORY:\n"
    f"{OUTPUT_DIR}"
)

log("")

log(
    f"SCANS TO PROCESS:\n"
    f"{SCANS}"
)

success = 0
failed = 0

for scan in SCANS:

    try:

        process_scan(scan)

        success += 1

    except Exception as e:

        failed += 1

        log("")
        log(
            f"FAILED SCAN "
            f"{scan}"
        )

        log(str(e))

        log("")

# ============================================================
# SUMMARY
# ============================================================

log("")
log("=" * 80)
log("SUMMARY")
log("=" * 80)

log(
    f"Successful scans : "
    f"{success}"
)

log(
    f"Failed scans     : "
    f"{failed}"
)

log("")

log(
    f"Output folder:\n"
    f"{OUTPUT_DIR}"
)

log("")

log(
    f"Log file:\n"
    f"{LOGFILE}"
)

print("\nFinished.")