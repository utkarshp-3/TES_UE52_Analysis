#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=====================================================================
RIXS PROCESSING SCRIPT
=====================================================================

Workflow
--------
1. Load all scans in the range (missing / mismatched scans are skipped
   and listed in the summary at the end).
2. Show the averaged energy-loss map, then ask for the cut positions:
     - Constant Incident Energy (CIE) cuts
     - Constant Charge Transfer (CCT) cuts
     - Constant Emission Energy (CEE) cuts
   (press Enter to skip a cut type)
3. Process every scan INDIVIDUALLY:
     - store its map in the HDF5 file (group scans/scanNN)
     - save its energy-loss map as PNG
     - extract and save all requested cuts
4. Average the scans, save the average to HDF5 (same "raw/avg_*" paths
   as before), and extract + save the cuts of the averaged map.
5. Plot the averaged RIXS map with all cut positions, and every cut with
   the individual scans overlaid (faint) and the average (black).
   All plots are also saved as PNG.
6. Print a run summary.

Output (XX_YY = scan range)
------
folder_path/
  RIXS_avg_direct_XX_YY.h5          raw/avg_*  +  scans/scanNN/*
  CIE_cuts_XX_YY/                   averaged cuts (same names as before)
      individual_scans/             scanNN_CIE_...txt
  CCT_cuts_XX_YY/   (same layout)
  CEE_cuts_XX_YY/   (same layout)
  RIXS_plots_XX_YY/                 PNGs (per-scan maps, average map, cuts)

Author: Utkarsh Prakash
=====================================================================
"""

import os
import numpy as np
import matplotlib.pyplot as plt
import h5py

# =====================================================================
# SETTINGS
# =====================================================================

folder_path = '/Users/utkarshprakash/Documents/Phd/Beamtime/Data/TES Beamtime/How_to_process_tesdata/Kushal_Sample0/Processed'

LOSS_MIN, LOSS_MAX = -10, 30      # energy-loss range used for plots and loss cuts


# =====================================================================
# HELPERS
# =====================================================================

def ask_int(prompt):
    while True:
        try:
            return int(input(prompt).strip())
        except ValueError:
            print("  Please enter a whole number.")


def ask_float_list(prompt):
    while True:
        txt = input(prompt).strip()
        if not txt:
            return []
        try:
            return [float(x) for x in txt.split(",") if x.strip()]
        except ValueError:
            print("  Please enter numbers separated by commas (or press Enter to skip).")


def save_txt(path, cols, header):
    np.savetxt(path, np.column_stack(cols), fmt="%.6f", header=header, comments='')


def show_now():
    """Display open figures without blocking the script (Spyder and terminal)."""
    plt.show(block=False)
    plt.pause(0.5)


def draw_loss_map(ax, mono, emission, counts, title):
    pcm = ax.pcolormesh(mono, mono - emission, counts, shading='auto', cmap='Spectral_r')
    ax.set_xlabel("Incident Energy (eV)")
    ax.set_ylabel("Energy Loss (eV)")
    ax.set_title(title)
    ax.set_ylim(LOSS_MIN, LOSS_MAX)
    return pcm


# =====================================================================
# CUT FUNCTIONS (used for each scan AND for the average)
# =====================================================================

def map_axes(mono, emission):
    return mono - emission, np.mean(mono, axis=0), emission[:, 0]


def cie_cut(mono, emission, counts, value):
    """Constant incident energy: one column of the map."""
    loss, mono_axis, _ = map_axes(mono, emission)
    idx = int(np.argmin(np.abs(mono_axis - value)))
    mask = (loss[:, idx] >= LOSS_MIN) & (loss[:, idx] <= LOSS_MAX)
    return dict(actual=mono_axis[idx],
                loss=loss[mask, idx],
                emission=emission[mask, idx],
                intensity=counts[mask, idx])


def cct_cut(mono, emission, counts, value):
    """Constant energy loss: in every column, the row closest to that loss."""
    loss, mono_axis, _ = map_axes(mono, emission)
    rows = np.argmin(np.abs(loss - value), axis=0)
    cols = np.arange(loss.shape[1])
    return dict(actual=value,
                incident=mono_axis,
                emission=emission[rows, cols],
                intensity=counts[rows, cols])


def cee_cut(mono, emission, counts, value):
    """Constant emission energy: one row of the map."""
    _, mono_axis, em_axis = map_axes(mono, emission)
    idx = int(np.argmin(np.abs(em_axis - value)))
    actual = em_axis[idx]
    intensity = counts[idx, :]
    loss = mono_axis - actual
    mask = (loss >= LOSS_MIN) & (loss <= LOSS_MAX)
    return dict(actual=actual,
                incident=mono_axis,
                intensity=intensity,
                loss=loss[mask],
                intensity_loss=intensity[mask])


# Save functions — headers keep the same number of lines as the original script

def save_cie(cut, folder, prefix, label, who):
    save_txt(os.path.join(folder, f"{prefix}CIE_Loss_{label:.2f}eV.txt"),
             (cut["loss"], cut["intensity"]),
             f"CIE Cut ({who})\nIncident Energy = {cut['actual']:.2f} eV\nColumns:\nEnergyLoss Intensity")
    save_txt(os.path.join(folder, f"{prefix}CIE_Emission_{label:.2f}eV.txt"),
             (cut["emission"], cut["intensity"]),
             f"CIE Cut ({who})\nIncident Energy = {cut['actual']:.2f} eV\nColumns:\nEmissionEnergy Intensity")


def save_cct(cut, folder, prefix, label, who):
    save_txt(os.path.join(folder, f"{prefix}CCT_Incident_{label:.2f}eV.txt"),
             (cut["incident"], cut["intensity"]),
             f"CCT Cut ({who})\nEnergy Loss = {cut['actual']:.2f} eV\nColumns:\nIncidentEnergy Intensity")
    save_txt(os.path.join(folder, f"{prefix}CCT_Emission_{label:.2f}eV.txt"),
             (cut["emission"], cut["intensity"]),
             f"CCT Cut ({who})\nEnergy Loss = {cut['actual']:.2f} eV\nColumns:\nEmissionEnergy Intensity")


def save_cee(cut, folder, prefix, label, who):
    save_txt(os.path.join(folder, f"{prefix}CEE_Incident_{label:.2f}eV.txt"),
             (cut["incident"], cut["intensity"]),
             f"CEE Cut at Emission Energy {cut['actual']:.2f} eV ({who})\nColumns: IncidentEnergy  Intensity")
    save_txt(os.path.join(folder, f"{prefix}CEE_Loss_{label:.2f}eV.txt"),
             (cut["loss"], cut["intensity_loss"]),
             f"CEE Cut projected onto energy loss ({who})\nEmission Energy = {cut['actual']:.2f} eV\n"
             f"Columns: EnergyLoss  Intensity")


CUT_TYPES = {
    "cie": dict(func=cie_cut, save=save_cie, name="CIE"),
    "cct": dict(func=cct_cut, save=save_cct, name="CCT"),
    "cee": dict(func=cee_cut, save=save_cee, name="CEE"),
}


# =====================================================================
# USER INPUT: SCAN RANGE
# =====================================================================

while True:
    start_xxx = ask_int("Enter start scan number: ")
    end_xxx   = ask_int("Enter end scan number: ")
    if end_xxx >= start_xxx:
        break
    print("  End must be greater than or equal to start.")

rng = f"{start_xxx:02d}_{end_xxx:02d}"
scan_label = f"Scans {start_xxx}–{end_xxx}"


# =====================================================================
# STEP 1: LOAD ALL SCANS
# =====================================================================

scans = []
skipped = []            # (scan number, reason)
reference_shape = None

print("\n--- Loading scans ---")
for xxx in range(start_xxx, end_xxx + 1):
    name = f"scan{xxx:02}"
    file_path = os.path.join(folder_path, f"{name}.npz")

    if not os.path.exists(file_path):
        skipped.append((xxx, f"{name}.npz missing"))
        continue

    try:
        with np.load(file_path) as data:
            mono     = data['mono']
            emission = data['emission']
            counts   = data['counts']

        if reference_shape is None:
            reference_shape = counts.shape
        elif counts.shape != reference_shape:
            skipped.append((xxx, f"shape mismatch {counts.shape} vs {reference_shape}"))
            continue

        scans.append(dict(num=xxx, name=name, mono=mono, emission=emission, counts=counts))
        print(f"Loaded {name}.npz")

    except Exception as e:
        skipped.append((xxx, f"error while loading: {e}"))


def print_summary(cuts_done=None, n_png=0):
    line = "=" * 60
    print(f"\n{line}\n RUN SUMMARY\n{line}")
    print(f" Scans requested : {start_xxx}–{end_xxx} ({end_xxx - start_xxx + 1})")
    loaded = ", ".join(str(s["num"]) for s in scans) or "none"
    print(f" Loaded          : {len(scans)}  ->  {loaded}")
    print(f" Skipped         : {len(skipped)}")
    for num, reason in skipped:
        print(f"     scan {num}: {reason}")
    if cuts_done is not None:
        for key, vals in cuts_done.items():
            txt = ", ".join(f"{v:.2f}" for v in vals) if vals else "none"
            print(f" {CUT_TYPES[key]['name']} cuts        : {txt} eV")
        print(f" HDF5 file       : {save_path}")
        print(f" Plots           : {n_png} PNGs in {png_folder}")
    print(line)


if not scans:
    print_summary()
    raise RuntimeError("No valid scans loaded.")


# =====================================================================
# STEP 2: SHOW AVERAGED MAP, ASK FOR CUT POSITIONS
# =====================================================================

avg_mono     = np.mean([s["mono"] for s in scans], axis=0)
avg_emission = np.mean([s["emission"] for s in scans], axis=0)
avg_counts   = np.mean([s["counts"] for s in scans], axis=0)
avg_loss, mono_axis, emission_axis = map_axes(avg_mono, avg_emission)

preview, pax = plt.subplots(figsize=(9, 7))
pcm = draw_loss_map(pax, avg_mono, avg_emission, avg_counts,
                    f"RIXS Energy-Loss Map (average)\n{scan_label}")
preview.colorbar(pcm, ax=pax, label="Counts (a.u.)")
show_now()

print(f"\nIncident energy : {mono_axis.min():.2f} – {mono_axis.max():.2f} eV")
print(f"Emission energy : {emission_axis.min():.2f} – {emission_axis.max():.2f} eV")

requested = {
    "cie": ask_float_list("\nEnter incident energies for CIE cuts (comma-separated, Enter to skip): "),
    "cct": ask_float_list("\nEnter energy-loss values for CCT cuts (comma-separated, Enter to skip): "),
    "cee": ask_float_list("\nEnter emission energies for CEE cuts (comma-separated, Enter to skip): "),
}
plt.close(preview)

# Cuts of the averaged map (their actual energies label the files of every scan)
avg_cuts = {key: [CUT_TYPES[key]["func"](avg_mono, avg_emission, avg_counts, v) for v in vals]
            for key, vals in requested.items()}

# Output folders
save_path  = os.path.join(folder_path, f"RIXS_avg_direct_{rng}.h5")
png_folder = os.path.join(folder_path, f"RIXS_plots_{rng}")
os.makedirs(png_folder, exist_ok=True)

cut_folders = {}
for key, vals in requested.items():
    if vals:
        f = os.path.join(folder_path, f"{CUT_TYPES[key]['name']}_cuts_{rng}")
        os.makedirs(os.path.join(f, "individual_scans"), exist_ok=True)
        cut_folders[key] = f

n_png = 0


def save_png(fig, fname, close=True):
    global n_png
    fig.tight_layout()
    fig.savefig(os.path.join(png_folder, fname), dpi=300, bbox_inches="tight")
    n_png += 1
    if close:
        plt.close(fig)


# =====================================================================
# STEP 3: PROCESS + SAVE EACH SCAN INDIVIDUALLY
# STEP 4: AVERAGE + SAVE
# =====================================================================

with h5py.File(save_path, 'w') as hf:
    hf.attrs["scan_range"] = f"{start_xxx}-{end_xxx}"
    hf.attrs["scans_used"] = np.array([s["num"] for s in scans])

    # ---------------- Individual scans ----------------
    print("\n--- Processing individual scans ---")
    for s in scans:
        name = s["name"]

        g = hf.create_group(f"scans/{name}")
        g.create_dataset("mono", data=s["mono"])
        g.create_dataset("emission", data=s["emission"])
        g.create_dataset("counts", data=s["counts"])
        g.create_dataset("energy_loss", data=s["mono"] - s["emission"])

        fig, ax = plt.subplots(figsize=(9, 7))
        pcm = draw_loss_map(ax, s["mono"], s["emission"], s["counts"],
                            f"RIXS Energy-Loss Map\n{name}")
        fig.colorbar(pcm, ax=ax, label="Counts (a.u.)")
        save_png(fig, f"{name}_rixs_map.png")

        for key, vals in requested.items():
            ct = CUT_TYPES[key]
            s[key] = []
            for v, avg_cut in zip(vals, avg_cuts[key]):
                cut = ct["func"](s["mono"], s["emission"], s["counts"], v)
                ct["save"](cut, os.path.join(cut_folders[key], "individual_scans"),
                           f"{name}_", avg_cut["actual"], name)
                s[key].append(cut)

        print(f"Processed + saved {name}")

    # ---------------- Average ----------------
    grp = hf.create_group("raw")
    grp.create_dataset("avg_mono", data=avg_mono)
    grp.create_dataset("avg_emission", data=avg_emission)
    grp.create_dataset("avg_counts", data=avg_counts)
    grp.create_dataset("avg_energy_loss", data=avg_loss)

print(f"\n✅ Saved individual + averaged maps → {save_path}")

who_avg = f"average of scans {start_xxx}-{end_xxx}"
for key, cuts in avg_cuts.items():
    for cut in cuts:
        CUT_TYPES[key]["save"](cut, cut_folders[key], "", cut["actual"], who_avg)
        print(f"💾 Saved averaged {CUT_TYPES[key]['name']} cut {cut['actual']:.2f} eV")


# =====================================================================
# STEP 5: PLOTS
# =====================================================================

legend_kw = dict(fontsize=8, ncol=2) if len(scans) <= 16 else None


def overlay_plot(key, i, xkey, ykey, xlabel, title, fname, xlim=None):
    fig, ax = plt.subplots(figsize=(7, 5))
    for s in scans:
        c = s[key][i]
        ax.plot(c[xkey], c[ykey], lw=1, alpha=0.35, label=f"Scan {s['num']}")
    a = avg_cuts[key][i]
    ax.plot(a[xkey], a[ykey], color="k", lw=2.5, label="Average")
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Intensity (a.u.)")
    ax.set_title(title)
    if xlim:
        ax.set_xlim(*xlim)
    ax.grid(True, alpha=0.3)
    if legend_kw:
        ax.legend(**legend_kw)
    save_png(fig, fname, close=False)


# ---- Averaged RIXS map with cut positions ----
fig_map, ax_map = plt.subplots(figsize=(10, 8))
pcm = draw_loss_map(ax_map, avg_mono, avg_emission, avg_counts,
                    f"RIXS Energy-Loss Map (average)\n{scan_label}")
fig_map.colorbar(pcm, ax=ax_map, label="Counts (a.u.)")

for c, cut in zip(plt.cm.plasma(np.linspace(0, 1, max(len(avg_cuts["cie"]), 1))), avg_cuts["cie"]):
    ax_map.axvline(cut["actual"], color=c, lw=2, ls='--', alpha=0.9,
                   label=f'CIE {cut["actual"]:.2f} eV')
for c, cut in zip(plt.cm.viridis(np.linspace(0, 1, max(len(avg_cuts["cct"]), 1))), avg_cuts["cct"]):
    ax_map.plot(mono_axis, np.full_like(mono_axis, cut["actual"]), color=c, lw=2, ls='-.',
                alpha=0.9, label=f'CCT {cut["actual"]:.2f} eV')
for c, cut in zip(plt.cm.cool(np.linspace(0, 1, max(len(avg_cuts["cee"]), 1))), avg_cuts["cee"]):
    ax_map.plot(mono_axis, mono_axis - cut["actual"], color=c, lw=2.5, ls=':',
                label=f'CEE {cut["actual"]:.2f} eV')

if any(avg_cuts.values()):
    ax_map.legend(fontsize=8, loc='upper right', framealpha=0.9)
save_png(fig_map, f"avg_rixs_map_{rng}.png", close=False)

# ---- Cut plots: individual scans + average ----
for i, cut in enumerate(avg_cuts["cie"]):
    e = cut["actual"]
    overlay_plot("cie", i, "loss", "intensity", "Energy Loss (eV)",
                 f"CIE Cut\nEi = {e:.2f} eV", f"CIE_Loss_{e:.2f}eV.png")
    overlay_plot("cie", i, "emission", "intensity", "Emission Energy (eV)",
                 f"CIE Cut\nEi = {e:.2f} eV\nEmission Energy Projection", f"CIE_Emission_{e:.2f}eV.png")

for i, cut in enumerate(avg_cuts["cct"]):
    e = cut["actual"]
    overlay_plot("cct", i, "incident", "intensity", "Incident Energy (eV)",
                 f"CCT Cut\nEnergy Loss = {e:.2f} eV", f"CCT_Incident_{e:.2f}eV.png")
    overlay_plot("cct", i, "emission", "intensity", "Emission Energy (eV)",
                 f"CCT Cut\nEnergy Loss = {e:.2f} eV\nEmission Projection", f"CCT_Emission_{e:.2f}eV.png")

for i, cut in enumerate(avg_cuts["cee"]):
    e = cut["actual"]
    overlay_plot("cee", i, "incident", "intensity", "Incident Energy (eV)",
                 f"CEE Cut at Emission Energy = {e:.2f} eV\nIncident Energy Representation",
                 f"CEE_Incident_{e:.2f}eV.png")
    overlay_plot("cee", i, "loss", "intensity_loss", "Energy Loss (eV)",
                 f"CEE Cut at Emission Energy = {e:.2f} eV\nProjected onto Energy Transfer",
                 f"CEE_Loss_{e:.2f}eV.png", xlim=(LOSS_MIN, LOSS_MAX))


# =====================================================================
# STEP 6: SUMMARY + SHOW
# =====================================================================

print_summary(cuts_done={k: [c["actual"] for c in v] for k, v in avg_cuts.items()}, n_png=n_png)
print("\n🎉 RIXS processing complete.")
plt.show()
