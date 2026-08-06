#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jan 21 10:26:43 2026

@author: utkarshprakash
"""


import numpy as np
import matplotlib.pyplot as plt
import os

# Folder containing all scans
folder_path = '/Users/utkarshprakash/Documents/Phd/Beamtime/Data/TES Beamtime/How_to_process_tesdata/Kushal_Sample0/Processed'

# ==== USER INPUT ====
start_xxx = int(input("Enter the start of the range: "))
end_xxx   = int(input("Enter the end of the range: "))

print("\n--- PFY Integration Window (Emission Energy Range) ---")
y_start = float(input("Enter PFY integration lower bound (emission energy): "))
y_end   = float(input("Enter PFY integration upper bound (emission energy): "))


# ==== STORAGE ====
all_counts = []
all_mono = []
all_emission = []

all_pfy = []
all_pfy_energy = []

all_i0 = []
all_i0_energy = []
all_i0_raw = []
all_i0_raw_energy = []
loaded_scan_numbers = []

reference_shape = None


# ==========================================================
# ==== LOAD EACH SCAN AND PROCESS ==========================
# ==========================================================
for xxx in range(start_xxx, end_xxx + 1):

    scan_file = f"scan{xxx}.npz"
    scan_path = os.path.join(folder_path, scan_file)

    bld_file = f"scan{xxx}_bld.npz"
    bld_path = os.path.join(folder_path, bld_file)

    try:
        # ----------------------
        # Load RIXS scan
        # ----------------------
        data = np.load(scan_path)
        mono     = data[data.files[0]]
        emission = data[data.files[1]]
        counts   = data[data.files[2]]
        data.close()

        if reference_shape is None:
            reference_shape = counts.shape
        elif counts.shape != reference_shape:
            print(f"Skipping {scan_file}: shape mismatch.")
            continue

        all_counts.append(counts)
        all_mono.append(mono)
        all_emission.append(emission)
        loaded_scan_numbers.append(xxx)

        # ----------------------
        # Load beamline data
        # ----------------------
        bld = np.load(bld_path)
        i0     = bld[bld.files[0]]
        tey    = bld[bld.files[1]]
        diode1 = bld[bld.files[2]]
        sgm_en = bld[bld.files[3]]
        bld.close()

        x_values = mono[0, :]

        # ----------------------
        # Store I0 (raw + interpolated)
        # ----------------------
        if len(i0) != len(x_values):
            i0_interp = np.interp(x_values, sgm_en, i0)
        else:
            i0_interp = i0

        all_i0_raw.append(i0)
        all_i0_raw_energy.append(sgm_en)
        all_i0.append(i0_interp)
        all_i0_energy.append(x_values)

        # ----------------------
        # Compute PFY
        # ----------------------
        y_coords = emission[:, 0]

        y_start_idx = np.searchsorted(y_coords, y_start)
        y_end_idx   = np.searchsorted(y_coords, y_end)
        y_start_idx = np.clip(y_start_idx, 0, counts.shape[0] - 1)
        y_end_idx   = np.clip(y_end_idx,   0, counts.shape[0] - 1)

        selected_rows = counts[y_start_idx:y_end_idx + 1, :]
        selected_y    = y_coords[y_start_idx:y_end_idx + 1]

        pfy_raw = np.trapz(selected_rows, x=selected_y, axis=0)
        pfy_norm = pfy_raw / i0_interp

        all_pfy.append(pfy_norm)
        all_pfy_energy.append(x_values.copy())

        print(f"Loaded + processed {scan_file}")

    except Exception as e:
        print(f"Error loading {scan_file}: {e}")


# ==========================================================
# ==== AVERAGE RIXS MAP ===================================
# ==========================================================
if not all_counts:
    raise RuntimeError("No valid scans loaded.")

avg_counts = np.mean(np.array(all_counts), axis=0)
avg_mono   = np.mean(np.array(all_mono), axis=0)
avg_em     = np.mean(np.array(all_emission), axis=0)


save_folder = os.path.join(folder_path, "saved_output")
os.makedirs(save_folder, exist_ok=True)

# ==========================================================
# ==== PLOT RIXS MAP ======================================
# ==========================================================
plt.figure(figsize=(9, 7))
plt.pcolormesh(avg_mono, avg_em, avg_counts, shading="auto", cmap="viridis")
plt.xlabel("Mono (Incident Energy)")
plt.ylabel("Emission Energy (eV)")
plt.title(f"Avg RIXS Map — scans {start_xxx}–{end_xxx}")
plt.colorbar(label="Counts")
plt.tight_layout()
plt.savefig(os.path.join(save_folder, "avg_rixs_map.png"), dpi=300, bbox_inches="tight")
plt.show()


# ==========================================================
# ==== PFY AREA NORMALIZATION + AVERAGE ====================
# ==========================================================
pfy_axis = all_pfy_energy[0]
pfy_interp_norm = []

for energy, pfy in zip(all_pfy_energy, all_pfy):
    area = np.trapz(pfy, x=energy)
    pfy_norm = pfy / area
    pfy_interp_norm.append(np.interp(pfy_axis, energy, pfy_norm))

pfy_area_norm = np.array(pfy_interp_norm)
avg_pfy = np.mean(pfy_area_norm, axis=0)


# ==========================================================
# ==== PLOT PFY ============================================
# ==========================================================
plt.figure(figsize=(7, 5))
for pfy in pfy_area_norm:
    plt.plot(pfy_axis, pfy, alpha=0.3)

plt.plot(pfy_axis, avg_pfy, color='k', lw=2.5, label="Average PFY")
plt.xlabel("Incident Energy (eV)")
plt.ylabel("Normalized PFY (a.u.)")
plt.title(f"PFY {y_start}–{y_end} eV — scans {start_xxx}–{end_xxx}")
plt.grid(True, ls='--', alpha=0.4)
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(save_folder, "pfy_curves.png"), dpi=300, bbox_inches="tight")
plt.show()


# ==========================================================
# ==== PLOT I0 FOR ALL SCANS ===============================
# ==========================================================
plt.figure(figsize=(7, 5))
for idx, i0_curve in enumerate(all_i0):
    scan_num = loaded_scan_numbers[idx]
    plt.plot(all_i0_energy[idx], i0_curve, alpha=0.4, label=f"Scan {scan_num}")

avg_i0 = np.mean(np.array(all_i0), axis=0)
plt.plot(all_i0_energy[0], avg_i0, color='k', lw=2.5, label="Average I0")

plt.xlabel("Incident Energy (eV)")
plt.ylabel("I0 (a.u.)")
plt.title(f"I0 — scans {start_xxx}–{end_xxx}")
plt.grid(True, ls='--', alpha=0.4)
plt.legend(ncol=2, fontsize=9)
plt.tight_layout()
plt.savefig(os.path.join(save_folder, "i0_curves.png"), dpi=300, bbox_inches="tight")
plt.show()


# ==========================================================
# ==== SAVE OUTPUT ========================================
# ==========================================================

np.savetxt(os.path.join(save_folder, "avg_mono.txt"), avg_mono)
np.savetxt(os.path.join(save_folder, "avg_emission.txt"), avg_em)
np.savetxt(os.path.join(save_folder, "avg_rixs_counts.txt"), avg_counts)

for scan_num, e_raw, i_raw, e_int, i_int in zip(loaded_scan_numbers, all_i0_raw_energy, all_i0_raw, all_i0_energy, all_i0):
    np.savetxt(os.path.join(save_folder, f"i0_raw_scan{scan_num}.txt"),
               np.column_stack([e_raw, i_raw]),
               header="SGM_Energy(eV)   I0_Raw")
    np.savetxt(os.path.join(save_folder, f"i0_interp_scan{scan_num}.txt"),
               np.column_stack([e_int, i_int]),
               header="Mono_Energy(eV)   I0_Interpolated")

np.savetxt(os.path.join(save_folder, "pfy_norm_average.txt"),
           np.column_stack([pfy_axis, avg_pfy]),
           header="Incident_Energy(eV)   Averaged_Normalized_PFY")

# --- 2. Save individual raw PFY curves ---
for idx, pfy in enumerate(all_pfy):
    scan_num = loaded_scan_numbers[idx]
    filename = os.path.join(save_folder, f"pfy_raw_scan{scan_num}.txt")
    np.savetxt(filename, np.column_stack([pfy_axis, pfy]),
               header="Incident_Energy(eV)   PFY_Raw")

# --- 3. Save individual normalized PFY curves ---
for idx, pfy in enumerate(pfy_area_norm):
    scan_num = loaded_scan_numbers[idx]
    filename = os.path.join(save_folder, f"pfy_norm_scan{scan_num}.txt")
    np.savetxt(filename, np.column_stack([pfy_axis, pfy]),
               header="Incident_Energy(eV)   PFY_Normalized")

print("📁 Data saved successfully.")


print("\n✅ DONE — RIXS averaged, PFY extracted, I0 plotted.")
