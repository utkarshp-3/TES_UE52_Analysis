#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
INTEGRATED EMISSION SPECTRUM (XES)
=========================================================

Loads multiple TES RIXS scans,
averages them,
integrates horizontally over incident energy
(or a selected mono-energy window),
and produces an emission spectrum.

Author: Utkarsh Prakash
=========================================================
"""

import numpy as np
import matplotlib.pyplot as plt
import h5py
import os

# =========================================================
# USER INPUTS
# =========================================================

folder_path = folder_path ='/Users/utkarshprakash/Documents/Phd/Beamtime/Data/TES Beamtime/Novemeber/Analysis/Analysis/Ferrocynide/Vertical'

start_xxx = int(input("Enter start scan number: "))
end_xxx   = int(input("Enter end scan number: "))

# =========================================================
# LOAD SCANS
# =========================================================

all_counts = []
all_mono = []
all_emission = []

reference_shape = None

for xxx in range(start_xxx, end_xxx + 1):

    formatted_xxx = f"{xxx:02}"
    file_name = f"scan{formatted_xxx}.npz"
    file_path = os.path.join(folder_path, file_name)

    try:

        data = np.load(file_path)

        mono = data['mono']
        emission = data['emission']
        counts = data['counts']

        data.close()

        if reference_shape is None:
            reference_shape = counts.shape

        elif counts.shape != reference_shape:

            print(
                f"⚠️ Skipping {file_name}: "
                f"shape mismatch"
            )

            continue

        all_mono.append(mono)
        all_emission.append(emission)
        all_counts.append(counts)

        print(f"Loaded {file_name}")

    except Exception as e:

        print(
            f"Error loading {file_name}: {e}"
        )

if not all_counts:
    raise RuntimeError(
        "No valid scans loaded."
    )

# =========================================================
# AVERAGE DATA
# =========================================================

avg_mono = np.mean(
    np.array(all_mono),
    axis=0
)

avg_emission = np.mean(
    np.array(all_emission),
    axis=0
)

avg_counts = np.mean(
    np.array(all_counts),
    axis=0
)

# =========================================================
# SAVE AVERAGED DATA
# =========================================================

save_path = os.path.join(
    folder_path,
    f"Emission_avg_{start_xxx:02d}_{end_xxx:02d}.h5"
)

with h5py.File(save_path, 'w') as hf:

    grp = hf.create_group("raw")

    grp.create_dataset(
        "avg_mono",
        data=avg_mono
    )

    grp.create_dataset(
        "avg_emission",
        data=avg_emission
    )

    grp.create_dataset(
        "avg_counts",
        data=avg_counts
    )

    hf.attrs[
        "scan_range"
    ] = f"{start_xxx}-{end_xxx}"

print(
    f"\n✅ Saved averaged data → "
    f"{save_path}"
)

# =========================================================
# EMISSION AXIS
# =========================================================

emission_axis = avg_emission[:, 0]

# =========================================================
# MONO INTEGRATION RANGE
# =========================================================

use_limits = input(
    "\nLimit mono integration range? (y/n): "
).strip().lower()

if use_limits == 'y':

    mono_min = float(
        input("Enter minimum mono energy (eV): ")
    )

    mono_max = float(
        input("Enter maximum mono energy (eV): ")
    )

    # mono energy axis
    mono_axis = avg_mono[0, :]

    mono_mask = (
        (mono_axis >= mono_min)
        &
        (mono_axis <= mono_max)
    )

    if not np.any(mono_mask):

        raise ValueError(
            f"No mono points found between "
            f"{mono_min:.3f} and "
            f"{mono_max:.3f} eV"
        )

    print(
        f"\nIntegrating from "
        f"{mono_min:.3f} to "
        f"{mono_max:.3f} eV"
    )

    emission_spectrum = np.sum(
        avg_counts[:, mono_mask],
        axis=1
    )

else:

    print(
        "\nIntegrating over full mono range"
    )

    emission_spectrum = np.sum(
        avg_counts,
        axis=1
    )

# =========================================================
# OPTIONAL NORMALIZATION
# =========================================================

normalize = input(
    "\nNormalize spectrum? (y/n): "
).strip().lower()

if normalize == 'y':

    emission_spectrum = (
        emission_spectrum
        /
        np.max(emission_spectrum)
    )

# =========================================================
# PLOT EMISSION SPECTRUM
# =========================================================

plt.figure(
    figsize=(8, 6)
)

plt.plot(
    emission_axis,
    emission_spectrum,
    lw=2,
    color='black'
)

plt.xlabel(
    "Emission Energy (eV)"
)

plt.ylabel(
    "Integrated Intensity (a.u.)"
)

if use_limits == 'y':

    plt.title(
        f"Integrated Emission Spectrum\n"
        f"Mono = {mono_min:.2f}–{mono_max:.2f} eV\n"
        f"Scans {start_xxx}-{end_xxx}"
    )

else:

    plt.title(
        f"Integrated Emission Spectrum\n"
        f"Scans {start_xxx}-{end_xxx}"
    )

plt.grid(
    True,
    alpha=0.3
)

plt.tight_layout()
plt.show()

# =========================================================
# SAVE SPECTRUM
# =========================================================

if use_limits == 'y':

    output_file = os.path.join(
        folder_path,
        f"EmissionSpectrum_"
        f"{start_xxx:02d}_"
        f"{end_xxx:02d}_"
        f"{mono_min:.1f}_"
        f"{mono_max:.1f}eV.txt"
    )

else:

    output_file = os.path.join(
        folder_path,
        f"EmissionSpectrum_"
        f"{start_xxx:02d}_"
        f"{end_xxx:02d}.txt"
    )

np.savetxt(
    output_file,
    np.column_stack(
        (
            emission_axis,
            emission_spectrum
        )
    ),
    fmt="%.6f",
    header=(
        "Integrated Emission Spectrum\n"
        "Columns:\n"
        "EmissionEnergy(eV) Intensity"
    ),
    comments=''
)

print(
    f"\n💾 Saved spectrum → "
    f"{output_file}"
)

print(
    "\n🎉 Emission spectrum extraction complete."
)