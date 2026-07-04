#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=====================================================================
RIXS PROCESSING SCRIPT
=====================================================================

Features
--------
1. Load multiple .npz scans
2. Average scans directly
3. Save averaged data to HDF5
4. Plot RIXS energy-loss map
5. Generate:
    - Constant Incident Energy (CIE) cuts
    - Constant Charge Transfer (CCT) cuts
    - Constant Emission Energy (CEE) cuts
6. Draw cut positions directly on the RIXS plane
7. Save all cuts as text files

Author: Utkarsh Prakash
=====================================================================
"""

import numpy as np
import matplotlib.pyplot as plt
import h5py
import os

# =====================================================================
# USER INPUTS
# =====================================================================

folder_path ='/Users/utkarshprakash/Documents/Phd/Beamtime/Data/TES Beamtime/Novemeber/Analysis/Analysis/Ferrocynide/Horizontal'

start_xxx = int(input("Enter start scan number: "))
end_xxx   = int(input("Enter end scan number: "))

# =====================================================================
# LOAD SCANS
# =====================================================================

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

        # Shape consistency check
        if reference_shape is None:
            reference_shape = counts.shape

        elif counts.shape != reference_shape:
            print(f"⚠️ Skipping {file_name}: shape mismatch")
            continue

        all_mono.append(mono)
        all_emission.append(emission)
        all_counts.append(counts)

        print(f"Loaded {file_name}")

    except Exception as e:
        print(f"Error loading {file_name}: {e}")

if not all_counts:
    raise RuntimeError("No valid scans loaded.")

# =====================================================================
# AVERAGE DATA
# =====================================================================

avg_mono = np.mean(np.array(all_mono), axis=0)
avg_emission = np.mean(np.array(all_emission), axis=0)
avg_counts = np.mean(np.array(all_counts), axis=0)

# =====================================================================
# SAVE TO HDF5
# =====================================================================

save_path = os.path.join(
    folder_path,
    f"RIXS_avg_direct_{start_xxx:02d}_{end_xxx:02d}.h5"
)

with h5py.File(save_path, 'w') as hf:

    grp = hf.create_group("raw")

    grp.create_dataset("avg_mono", data=avg_mono)
    grp.create_dataset("avg_emission", data=avg_emission)
    grp.create_dataset("avg_counts", data=avg_counts)

    hf.attrs["scan_range"] = f"{start_xxx}-{end_xxx}"

print(f"\n✅ Saved averaged data → {save_path}")

# =====================================================================
# RELOAD DATA
# =====================================================================

with h5py.File(save_path, 'r') as hf:

    avg_mono = hf["raw/avg_mono"][:]
    avg_emission = hf["raw/avg_emission"][:]
    avg_counts = hf["raw/avg_counts"][:]

# =====================================================================
# ENERGY LOSS
# =====================================================================

energy_loss = avg_mono - avg_emission

# Axes
mono_axis = np.mean(avg_mono, axis=0)
emission_axis = avg_emission[:, 0]

# =====================================================================
# PLOT BASE RIXS MAP
# =====================================================================

fig, ax = plt.subplots(figsize=(10, 8))

pcm = ax.pcolormesh(
    avg_mono,
    energy_loss,
    avg_counts,
    shading='auto',
    cmap='Spectral_r'
)

ax.set_xlabel("Incident Energy (eV)")
ax.set_ylabel("Energy Loss (eV)")

ax.set_title(
    f"RIXS Energy-Loss Map\n"
    f"Scans {start_xxx}–{end_xxx}"
)

ax.set_ylim(-10, 30)

plt.colorbar(pcm, ax=ax, label="Counts (a.u.)")

# =====================================================================
# CONSTANT INCIDENT ENERGY (CIE) CUTS
# =====================================================================

cie_input = input(
    "\nEnter incident energies for CIE cuts "
    "(comma-separated): "
)

if cie_input.strip():

    cie_list = [
        float(x.strip())
        for x in cie_input.split(",")
        if x.strip()
    ]

    cie_colors = plt.cm.plasma(
        np.linspace(0, 1, len(cie_list))
    )

    cie_save_folder = os.path.join(
        folder_path,
        f"CIE_cuts_{start_xxx:02d}_{end_xxx:02d}"
    )

    os.makedirs(cie_save_folder, exist_ok=True)

    for c, cie in zip(cie_colors, cie_list):

        # ============================================================
        # FIND CLOSEST INCIDENT ENERGY
        # ============================================================

        idx = np.argmin(np.abs(mono_axis - cie))

        cie_actual = mono_axis[idx]

        cie_spectrum = avg_counts[:, idx]

        loss_axis = energy_loss[:, idx]

        emission_axis_cut = avg_emission[:, idx]

        # ============================================================
        # MARK CUT ON RIXS MAP
        # ============================================================

        ax.axvline(
            cie_actual,
            color=c,
            lw=2,
            ls='--',
            alpha=0.9,
            label=f'CIE {cie_actual:.2f} eV'
        )

        # ============================================================
        # ENERGY LOSS REPRESENTATION
        # ============================================================

        mask = (
            (loss_axis >= -10)
            &
            (loss_axis <= 30)
        )

        loss_axis_cut = loss_axis[mask]

        cie_spectrum_loss = cie_spectrum[mask]

        plt.figure(figsize=(7,5))

        plt.plot(
            loss_axis_cut,
            cie_spectrum_loss,
            color=c,
            lw=2
        )

        plt.xlabel("Energy Loss (eV)")
        plt.ylabel("Intensity (a.u.)")

        plt.title(
            f"CIE Cut\n"
            f"Ei = {cie_actual:.2f} eV"
        )

        plt.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.show()

        # ============================================================
        # EMISSION ENERGY REPRESENTATION
        # ============================================================

        emission_axis_proj = emission_axis_cut[mask]

        plt.figure(figsize=(7,5))

        plt.plot(
            emission_axis_proj,
            cie_spectrum_loss,
            color=c,
            lw=2
        )

        plt.xlabel("Emission Energy (eV)")
        plt.ylabel("Intensity (a.u.)")

        plt.title(
            f"CIE Cut\n"
            f"Ei = {cie_actual:.2f} eV\n"
            f"Emission Energy Projection"
        )

        plt.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.show()

        # ============================================================
        # SAVE ENERGY LOSS VERSION
        # ============================================================

        loss_file = os.path.join(
            cie_save_folder,
            f"CIE_Loss_{cie_actual:.2f}eV.txt"
        )

        np.savetxt(
            loss_file,
            np.column_stack(
                (
                    loss_axis_cut,
                    cie_spectrum_loss
                )
            ),
            fmt="%.6f",
            header=(
                f"CIE Cut\n"
                f"Incident Energy = "
                f"{cie_actual:.2f} eV\n"
                f"Columns:\n"
                f"EnergyLoss Intensity"
            ),
            comments=''
        )

        # ============================================================
        # SAVE EMISSION VERSION
        # ============================================================

        emission_file = os.path.join(
            cie_save_folder,
            f"CIE_Emission_{cie_actual:.2f}eV.txt"
        )

        np.savetxt(
            emission_file,
            np.column_stack(
                (
                    emission_axis_proj,
                    cie_spectrum_loss
                )
            ),
            fmt="%.6f",
            header=(
                f"CIE Cut\n"
                f"Incident Energy = "
                f"{cie_actual:.2f} eV\n"
                f"Columns:\n"
                f"EmissionEnergy Intensity"
            ),
            comments=''
        )

        print(
            f"💾 Saved CIE cut "
            f"{cie_actual:.2f} eV"
        )

# =====================================================================
# CONSTANT CHARGE TRANSFER (CCT) CUTS
# =====================================================================

cct_input = input(
    "\nEnter energy-loss values for CCT cuts "
    "(comma-separated): "
)

if cct_input.strip():

    cct_list = [
        float(x.strip())
        for x in cct_input.split(",")
        if x.strip()
    ]

    cct_colors = plt.cm.viridis(
        np.linspace(0, 1, len(cct_list))
    )

    cct_save_folder = os.path.join(
        folder_path,
        f"CCT_cuts_{start_xxx:02d}_{end_xxx:02d}"
    )

    os.makedirs(
        cct_save_folder,
        exist_ok=True
    )

    for c, cct in zip(
        cct_colors,
        cct_list
    ):

        # ============================================================
        # EXTRACT CONSTANT ENERGY LOSS CUT
        # ============================================================

        cct_spectrum = []

        cct_emission = []

        for j in range(len(mono_axis)):

            loss_col = energy_loss[:, j]

            idx = np.argmin(
                np.abs(
                    loss_col - cct
                )
            )

            cct_spectrum.append(
                avg_counts[idx, j]
            )

            cct_emission.append(
                avg_emission[idx, j]
            )

        cct_spectrum = np.array(
            cct_spectrum
        )

        cct_emission = np.array(
            cct_emission
        )

        # ============================================================
        # DRAW CUT ON RIXS MAP
        # ============================================================

        ax.plot(
            mono_axis,
            np.full_like(
                mono_axis,
                cct
            ),
            color=c,
            lw=2,
            ls='-.',
            alpha=0.9,
            label=f'CCT {cct:.2f} eV'
        )

        # ============================================================
        # INCIDENT ENERGY REPRESENTATION
        # ============================================================

        plt.figure(figsize=(7,5))

        plt.plot(
            mono_axis,
            cct_spectrum,
            color=c,
            lw=2
        )

        plt.xlabel(
            "Incident Energy (eV)"
        )

        plt.ylabel(
            "Intensity (a.u.)"
        )

        plt.title(
            f"CCT Cut\n"
            f"Energy Loss = "
            f"{cct:.2f} eV"
        )

        plt.grid(
            True,
            alpha=0.3
        )

        plt.tight_layout()
        plt.show()

        # ============================================================
        # EMISSION ENERGY REPRESENTATION
        # ============================================================

        plt.figure(figsize=(7,5))

        plt.plot(
            cct_emission,
            cct_spectrum,
            color=c,
            lw=2
        )

        plt.xlabel(
            "Emission Energy (eV)"
        )

        plt.ylabel(
            "Intensity (a.u.)"
        )

        plt.title(
            f"CCT Cut\n"
            f"Energy Loss = "
            f"{cct:.2f} eV\n"
            f"Emission Projection"
        )

        plt.grid(
            True,
            alpha=0.3
        )

        plt.tight_layout()
        plt.show()

        # ============================================================
        # SAVE INCIDENT REPRESENTATION
        # ============================================================

        incident_file = os.path.join(
            cct_save_folder,
            f"CCT_Incident_{cct:.2f}eV.txt"
        )

        np.savetxt(
            incident_file,
            np.column_stack(
                (
                    mono_axis,
                    cct_spectrum
                )
            ),
            fmt="%.6f",
            header=(
                f"CCT Cut\n"
                f"Energy Loss = "
                f"{cct:.2f} eV\n"
                f"Columns:\n"
                f"IncidentEnergy Intensity"
            ),
            comments=''
        )

        # ============================================================
        # SAVE EMISSION REPRESENTATION
        # ============================================================

        emission_file = os.path.join(
            cct_save_folder,
            f"CCT_Emission_{cct:.2f}eV.txt"
        )

        np.savetxt(
            emission_file,
            np.column_stack(
                (
                    cct_emission,
                    cct_spectrum
                )
            ),
            fmt="%.6f",
            header=(
                f"CCT Cut\n"
                f"Energy Loss = "
                f"{cct:.2f} eV\n"
                f"Columns:\n"
                f"EmissionEnergy Intensity"
            ),
            comments=''
        )

        print(
            f"💾 Saved CCT cut "
            f"{cct:.2f} eV"
        )
# =====================================================================
# CONSTANT EMISSION ENERGY (CEE) CUTS
# =====================================================================

cee_input = input(
    "\nEnter emission energies for CEE cuts "
    "(comma-separated): "
)

if cee_input.strip():

    cee_list = [
        float(x.strip())
        for x in cee_input.split(",")
        if x.strip()
    ]

    cee_colors = plt.cm.cool(
        np.linspace(0, 1, len(cee_list))
    )

    cee_save_folder = os.path.join(
        folder_path,
        f"CEE_cuts_{start_xxx:02d}_{end_xxx:02d}"
    )

    os.makedirs(cee_save_folder, exist_ok=True)

    for c, cee in zip(cee_colors, cee_list):

        # Find closest emission-energy row
        idx = np.argmin(np.abs(emission_axis - cee))

        cee_actual = emission_axis[idx]

        cee_spectrum = avg_counts[idx, :]

        incident_axis = mono_axis

        # Energy transfer projection
        loss_axis = incident_axis - cee_actual

        # =====================================================
        # MARK CUT ON RIXS MAP
        # =====================================================

        # Horizontal cut in emission-energy coordinates
        cee_loss_line = mono_axis - cee_actual

        ax.plot(
            mono_axis,
            cee_loss_line,
            color=c,
            lw=2.5,
            ls=':',
            alpha=1.0,
            label=f'CEE {cee_actual:.2f} eV'
        )

        # =====================================================
        # PLOT 1: INCIDENT ENERGY REPRESENTATION
        # =====================================================

        plt.figure(figsize=(7, 5))

        plt.plot(
            incident_axis,
            cee_spectrum,
            color=c,
            lw=2
        )

        plt.xlabel("Incident Energy (eV)")
        plt.ylabel("Intensity (a.u.)")

        plt.title(
            f"CEE Cut at Emission Energy = "
            f"{cee_actual:.2f} eV\n"
            f"Incident Energy Representation"
        )

        plt.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.show()

        # =====================================================
        # PLOT 2: ENERGY LOSS REPRESENTATION
        # =====================================================

        mask = (loss_axis >= -10) & (loss_axis <= 30)

        loss_axis_cut = loss_axis[mask]
        cee_spectrum_cut = cee_spectrum[mask]

        plt.figure(figsize=(7, 5))

        plt.plot(
            loss_axis_cut,
            cee_spectrum_cut,
            color=c,
            lw=2
        )

        plt.xlabel("Energy Loss (eV)")
        plt.ylabel("Intensity (a.u.)")

        plt.title(
            f"CEE Cut at Emission Energy = "
            f"{cee_actual:.2f} eV\n"
            f"Projected onto Energy Transfer"
        )

        plt.xlim(-10, 30)

        plt.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.show()

        # =====================================================
        # SAVE FILES
        # =====================================================

        # Incident-energy representation
        incident_file = os.path.join(
            cee_save_folder,
            f"CEE_Incident_{cee_actual:.2f}eV.txt"
        )

        np.savetxt(
            incident_file,
            np.column_stack(
                (incident_axis, cee_spectrum)
            ),
            fmt="%.6f",
            header=(
                f"CEE Cut at Emission Energy "
                f"{cee_actual:.2f} eV\n"
                f"Columns: IncidentEnergy  Intensity"
            ),
            comments=''
        )

        # Energy-loss representation
        loss_file = os.path.join(
            cee_save_folder,
            f"CEE_Loss_{cee_actual:.2f}eV.txt"
        )

        np.savetxt(
            loss_file,
            np.column_stack(
                (loss_axis_cut, cee_spectrum_cut)
            ),
            fmt="%.6f",
            header=(
                f"CEE Cut projected onto energy loss\n"
                f"Emission Energy = {cee_actual:.2f} eV\n"
                f"Columns: EnergyLoss  Intensity"
            ),
            comments=''
        )

        print(f"💾 Saved CEE cuts for {cee_actual:.2f} eV")

# =====================================================================
# FINALIZE RIXS MAP
# =====================================================================

ax.legend(
    fontsize=8,
    loc='upper right',
    framealpha=0.9
)

plt.tight_layout()
plt.show()

# =====================================================================
# DONE
# =====================================================================

print("\n🎉 RIXS processing complete.")