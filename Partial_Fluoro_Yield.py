#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PFY / TEY processing for UE52 RIXS scans.

Workflow
--------
1. All scans in the range are loaded (RIXS map + beamline I0/TEY).
   Missing or mismatched scans are skipped and reported in the final summary.
2. The averaged RIXS map is shown with the available emission-energy range,
   and you enter the PFY window (it is asked again only if it is invalid).
3. Every scan is processed individually and saved:
     - PFY raw, PFY I0-normalized, PFY area-normalized
     - TEY (raw and I0-normalized)
     - I0 (raw on SGM axis and interpolated onto the mono axis)
4. Averages of all datasets (and the averaged RIXS map) are always computed and saved.
5. You are asked what to display: the averaged PFY
   (I0-normalized / area-normalized / both), the I0 plot, and the TEY plot
   (raw / I0-normalized / both).
   All plots, including a 2x2 overview figure (overview.png), are saved as PNG
   regardless; only the chosen ones are displayed.
6. A summary of the run is printed at the end.

Original author: utkarshprakash (2026-01-21)
"""

import os
import numpy as np
import matplotlib.pyplot as plt

# np.trapz was renamed np.trapezoid in NumPy 2.0
trapz = getattr(np, "trapezoid", None) or np.trapz

# Folder containing all scans
folder_path = '/Users/utkarshprakash/Documents/Phd/Beamtime/Data/TES Beamtime/How_to_process_tesdata/Kushal_Sample0/Processed'


# ==========================================================
# ==== HELPERS =============================================
# ==========================================================
def ask_yes_no(prompt):
    while True:
        ans = input(f"{prompt} [y/n]: ").strip().lower()
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False
        print("  Please answer y or n.")


def ask_choice(prompt, options):
    """options: dict {key: label}. Returns the chosen key."""
    print(prompt)
    for key, label in options.items():
        print(f"  {key}) {label}")
    while True:
        ans = input("Choice: ").strip()
        if ans in options:
            return ans
        print(f"  Please enter one of: {', '.join(options)}")


def ask_int(prompt):
    while True:
        try:
            return int(input(prompt).strip())
        except ValueError:
            print("  Please enter a whole number.")


def ask_float(prompt):
    while True:
        try:
            return float(input(prompt).strip())
        except ValueError:
            print("  Please enter a number.")


def save_columns(path, x, cols, header):
    np.savetxt(path, np.column_stack([x, *cols]), header=header)


def window_indices(y_coords, lo, hi):
    """Row indices of the PFY integration window (same logic as the original script)."""
    i_lo = int(np.clip(np.searchsorted(y_coords, lo), 0, len(y_coords) - 1))
    i_hi = int(np.clip(np.searchsorted(y_coords, hi), 0, len(y_coords) - 1))
    return i_lo, i_hi


def show_now():
    """Display open figures without blocking the script (works in Spyder and terminal)."""
    plt.show(block=False)
    plt.pause(0.5)


# ==========================================================
# ==== USER INPUT: SCAN RANGE ==============================
# ==========================================================
while True:
    start_xxx = ask_int("Enter the start of the range: ")
    end_xxx   = ask_int("Enter the end of the range: ")
    if end_xxx >= start_xxx:
        break
    print("  End must be greater than or equal to start.")

save_folder  = os.path.join(folder_path, "saved_output")
indiv_folder = os.path.join(save_folder, "individual_scans")
avg_folder   = os.path.join(save_folder, "averages")
for f in (save_folder, indiv_folder, avg_folder):
    os.makedirs(f, exist_ok=True)

E_HDR = "Incident_Energy(eV)"
scan_label = f"scans {start_xxx}–{end_xxx}"


# ==========================================================
# ==== STEP 1: LOAD ALL SCANS ==============================
# ==========================================================
scans = []
skipped = []          # list of (scan number, reason)
reference_shape = None

print("\n--- Loading scans ---")
for xxx in range(start_xxx, end_xxx + 1):
    tag = f"scan{xxx}"
    scan_path = os.path.join(folder_path, f"{tag}.npz")
    bld_path  = os.path.join(folder_path, f"{tag}_bld.npz")

    if not os.path.exists(scan_path):
        skipped.append((xxx, f"RIXS file {tag}.npz missing"))
        continue
    if not os.path.exists(bld_path):
        skipped.append((xxx, f"beamline file {tag}_bld.npz missing"))
        continue

    try:
        # ---- RIXS scan ----
        with np.load(scan_path) as data:
            mono     = data[data.files[0]]
            emission = data[data.files[1]]
            counts   = data[data.files[2]]

        if reference_shape is None:
            reference_shape = counts.shape
        elif counts.shape != reference_shape:
            skipped.append((xxx, f"shape mismatch {counts.shape} vs {reference_shape}"))
            continue

        # ---- Beamline data ----
        with np.load(bld_path) as bld:
            i0_raw  = bld[bld.files[0]]
            tey_raw = bld[bld.files[1]]
            diode1  = bld[bld.files[2]]   # kept for reference, not used
            sgm_en  = bld[bld.files[3]]

        x_values = mono[0, :].copy()

        # ---- Put I0 and TEY on the mono energy axis ----
        if len(i0_raw) != len(x_values):
            i0  = np.interp(x_values, sgm_en, i0_raw)
            tey = np.interp(x_values, sgm_en, tey_raw)
        else:
            i0  = i0_raw.copy()
            tey = tey_raw.copy()

        scans.append(dict(num=xxx, tag=tag, energy=x_values, mono=mono,
                          emission=emission, counts=counts,
                          i0_raw=i0_raw, tey_raw=tey_raw, sgm_en=sgm_en,
                          i0=i0, tey=tey, tey_i0=tey / i0))
        print(f"Loaded {tag}")

    except Exception as e:
        skipped.append((xxx, f"error while loading: {e}"))


def print_summary(window=None, n_rows=None, shown=None, n_png=0):
    n_req = end_xxx - start_xxx + 1
    line = "=" * 60
    print(f"\n{line}\n RUN SUMMARY\n{line}")
    print(f" Scans requested : {start_xxx}–{end_xxx} ({n_req})")
    loaded_nums = ", ".join(str(s["num"]) for s in scans) or "none"
    print(f" Loaded          : {len(scans)}  ->  {loaded_nums}")
    print(f" Skipped         : {len(skipped)}")
    for num, reason in skipped:
        print(f"     scan {num}: {reason}")
    if window is not None:
        print(f" PFY window      : {window[0]:.2f}–{window[1]:.2f} eV ({n_rows} emission rows)")
    if scans and window is not None:
        print(f" Saved           : {len(scans)} scans x 7 files in individual_scans/")
        print(f"                   averages in averages/, {n_png} PNG plots")
        print(f" Output folder   : {save_folder}")
    if shown is not None:
        print(f" Shown on screen : {', '.join(shown) if shown else 'nothing (all saved as PNG)'}")
    print(line)


if not scans:
    print_summary()
    raise RuntimeError("No valid scans loaded.")


# ==========================================================
# ==== AVERAGED RIXS MAP ===================================
# ==========================================================
avg_counts = np.mean([s["counts"] for s in scans], axis=0)
avg_mono   = np.mean([s["mono"] for s in scans], axis=0)
avg_em     = np.mean([s["emission"] for s in scans], axis=0)
em_axis    = avg_em[:, 0]
em_min, em_max = float(em_axis.min()), float(em_axis.max())
em_step = float(np.mean(np.abs(np.diff(em_axis)))) if len(em_axis) > 1 else 0.0


def draw_rixs_map(ax, window=None):
    mesh = ax.pcolormesh(avg_mono, avg_em, avg_counts, shading="auto", cmap="viridis")
    if window is not None:
        for y in window:
            ax.axhline(y, color="red", ls="--", lw=1.5)
        ax.text(0.02, 0.98, f"PFY window {window[0]:.2f}–{window[1]:.2f} eV",
                transform=ax.transAxes, va="top", color="red", fontsize=9,
                bbox=dict(facecolor="white", alpha=0.7, edgecolor="none"))
    ax.set_xlabel("Mono (Incident Energy)")
    ax.set_ylabel("Emission Energy (eV)")
    ax.set_title(f"Avg RIXS Map — {scan_label}")
    return mesh


# ==========================================================
# ==== STEP 2: CHOOSE PFY WINDOW FROM THE RIXS MAP =========
# ==========================================================
print("\n--- PFY Integration Window (Emission Energy Range) ---")
print(f"Emission energy in data: {em_min:.2f} – {em_max:.2f} eV "
      f"({len(em_axis)} rows, step ≈ {em_step:.3f} eV)")

preview = plt.figure(figsize=(8, 6))
draw_rixs_map(preview.gca())
preview.colorbar(preview.gca().collections[0], ax=preview.gca(), label="Counts")
show_now()

while True:
    y_start = ask_float("Enter PFY integration lower bound (emission energy): ")
    y_end   = ask_float("Enter PFY integration upper bound (emission energy): ")

    if y_end <= y_start:
        print("  Upper bound must be larger than lower bound. Try again.")
        continue
    if y_end < em_min or y_start > em_max:
        print(f"  Window is completely outside the data ({em_min:.2f}–{em_max:.2f} eV). Try again.")
        continue
    if y_start < em_min or y_end > em_max:
        print(f"  ⚠ Window extends beyond the data; it will be cut to "
              f"{max(y_start, em_min):.2f}–{min(y_end, em_max):.2f} eV.")

    break

i_lo, i_hi = window_indices(em_axis, y_start, y_end)
n_rows = i_hi - i_lo + 1
print(f"  Window covers {n_rows} emission rows "
      f"({em_axis[i_lo]:.2f}–{em_axis[i_hi]:.2f} eV).")
if n_rows < 3:
    print("  ⚠ Very few rows — the PFY will be noisy.")

plt.close(preview)


# ==========================================================
# ==== STEP 3: PROCESS + SAVE EACH SCAN INDIVIDUALLY =======
# ==========================================================
print("\n--- Processing scans ---")
for s in scans:
    tag, x_values = s["tag"], s["energy"]
    y_coords = s["emission"][:, 0]
    lo, hi = window_indices(y_coords, y_start, y_end)

    pfy_raw  = trapz(s["counts"][lo:hi + 1, :], x=y_coords[lo:hi + 1], axis=0)
    pfy_i0   = pfy_raw / s["i0"]
    pfy_area = pfy_i0 / trapz(pfy_i0, x=x_values)
    s.update(pfy_raw=pfy_raw, pfy_i0=pfy_i0, pfy_area=pfy_area)

    save_columns(os.path.join(indiv_folder, f"pfy_raw_{tag}.txt"),
                 x_values, [pfy_raw], f"{E_HDR}   PFY_Raw")
    save_columns(os.path.join(indiv_folder, f"pfy_I0norm_{tag}.txt"),
                 x_values, [pfy_i0], f"{E_HDR}   PFY_I0_Normalized")
    save_columns(os.path.join(indiv_folder, f"pfy_areanorm_{tag}.txt"),
                 x_values, [pfy_area], f"{E_HDR}   PFY_Area_Normalized")
    save_columns(os.path.join(indiv_folder, f"tey_{tag}.txt"),
                 x_values, [s["tey"], s["tey_i0"]], f"{E_HDR}   TEY_Raw   TEY_I0_Normalized")
    save_columns(os.path.join(indiv_folder, f"i0_interp_{tag}.txt"),
                 x_values, [s["i0"]], f"{E_HDR}   I0_Interpolated")
    save_columns(os.path.join(indiv_folder, f"beamline_raw_{tag}.txt"),
                 s["sgm_en"], [s["i0_raw"], s["tey_raw"]], "SGM_Energy(eV)   I0_Raw   TEY_Raw")
    # All columns in one file (handy for Origin)
    save_columns(os.path.join(indiv_folder, f"all_columns_{tag}.txt"),
                 x_values, [pfy_raw, pfy_i0, pfy_area, s["tey"], s["tey_i0"], s["i0"]],
                 f"{E_HDR}   PFY_Raw   PFY_I0norm   PFY_Areanorm   TEY_Raw   TEY_I0norm   I0")

    print(f"Processed + saved {tag}")

print(f"\n{len(scans)} scans processed. Individual files in:\n  {indiv_folder}")


# ==========================================================
# ==== STEP 4: AVERAGE + SAVE (ALWAYS) =====================
# ==========================================================
axis = scans[0]["energy"]
keys = ["pfy_raw", "pfy_i0", "pfy_area", "tey", "tey_i0", "i0"]

avgs = {}
for key in keys:
    stack = np.array([np.interp(axis, s["energy"], s[key]) for s in scans])
    avgs[key] = stack.mean(axis=0)

save_columns(os.path.join(avg_folder, "pfy_raw_average.txt"),
             axis, [avgs["pfy_raw"]], f"{E_HDR}   Averaged_PFY_Raw")
save_columns(os.path.join(avg_folder, "pfy_I0norm_average.txt"),
             axis, [avgs["pfy_i0"]], f"{E_HDR}   Averaged_PFY_I0_Normalized")
save_columns(os.path.join(avg_folder, "pfy_areanorm_average.txt"),
             axis, [avgs["pfy_area"]], f"{E_HDR}   Averaged_PFY_Area_Normalized")
save_columns(os.path.join(avg_folder, "tey_average.txt"),
             axis, [avgs["tey"], avgs["tey_i0"]],
             f"{E_HDR}   Averaged_TEY_Raw   Averaged_TEY_I0_Normalized")
save_columns(os.path.join(avg_folder, "i0_average.txt"),
             axis, [avgs["i0"]], f"{E_HDR}   Averaged_I0")
save_columns(os.path.join(avg_folder, "all_columns_average.txt"),
             axis, [avgs[k] for k in keys],
             f"{E_HDR}   PFY_Raw   PFY_I0norm   PFY_Areanorm   TEY_Raw   TEY_I0norm   I0")

np.savetxt(os.path.join(avg_folder, "avg_mono.txt"), avg_mono)
np.savetxt(os.path.join(avg_folder, "avg_emission.txt"), avg_em)
np.savetxt(os.path.join(avg_folder, "avg_rixs_counts.txt"), avg_counts)

print(f"Averages saved in:\n  {avg_folder}")


# ==========================================================
# ==== STEP 5: ASK WHAT TO SHOW ============================
# ==========================================================
show_overview = False   # overview.png is always saved; set True to also display it

show_i0_plot = show_area_plot = False
if ask_yes_no("\nShow the averaged PFY?"):
    choice = ask_choice("Which normalization do you want to see?",
                        {"1": "I0-normalized", "2": "Area-normalized", "3": "Both"})
    show_i0_plot   = choice in ("1", "3")
    show_area_plot = choice in ("2", "3")

show_i0_curves = ask_yes_no("\nShow the I0 plot?")

show_tey_raw = show_tey_i0 = False
if ask_yes_no("\nShow the TEY plot?"):
    choice = ask_choice("Which TEY do you want to see?",
                        {"1": "Raw TEY", "2": "I0-normalized TEY", "3": "Both"})
    show_tey_raw = choice in ("1", "3")
    show_tey_i0  = choice in ("2", "3")


# ==========================================================
# ==== PLOTS (all saved as PNG, only chosen ones shown) ====
# ==========================================================
legend_kw = dict(ncol=2, fontsize=8) if len(scans) <= 16 else None
pfy_tag = f"{y_start}–{y_end} eV"
n_png = 0


def draw_curves(ax, key, ylabel, title, legend=True):
    for s in scans:
        ax.plot(s["energy"], s[key], alpha=0.35, label=f"Scan {s['num']}")
    ax.plot(axis, avgs[key], color="k", lw=2.5, label="Average")
    ax.set_xlabel("Incident Energy (eV)")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True, ls="--", alpha=0.4)
    if legend and legend_kw:
        ax.legend(**legend_kw)


def finish(fig, fname, show):
    global n_png
    fig.tight_layout()
    fig.savefig(os.path.join(save_folder, fname), dpi=300, bbox_inches="tight")
    n_png += 1
    if not show:
        plt.close(fig)


def single_plot(key, ylabel, title, fname, show):
    fig, ax = plt.subplots(figsize=(7, 5))
    draw_curves(ax, key, ylabel, title)
    finish(fig, fname, show)


# ---- Overview 2x2 figure ----
fig, axs = plt.subplots(2, 2, figsize=(13, 9))
draw_curves(axs[0, 0], "pfy_i0", "PFY / I0 (a.u.)", f"PFY (I0-norm) {pfy_tag}")
draw_curves(axs[0, 1], "i0", "I0 (a.u.)", "I0", legend=False)
draw_curves(axs[1, 0], "tey_i0", "TEY / I0 (a.u.)", "TEY (I0-norm)", legend=False)
mesh = draw_rixs_map(axs[1, 1], window=(y_start, y_end))
fig.colorbar(mesh, ax=axs[1, 1], label="Counts")
fig.suptitle(f"Overview — {scan_label}", fontsize=14)
finish(fig, "overview.png", show_overview)

# ---- Individual figures ----
single_plot("pfy_i0", "PFY / I0 (a.u.)", f"PFY (I0-norm) {pfy_tag} — {scan_label}",
            "pfy_I0norm_curves.png", show_i0_plot)
single_plot("pfy_area", "Area-normalized PFY (a.u.)", f"PFY (area-norm) {pfy_tag} — {scan_label}",
            "pfy_areanorm_curves.png", show_area_plot)
single_plot("tey", "TEY (a.u.)", f"TEY (raw) — {scan_label}",
            "tey_raw_curves.png", show_tey_raw)
single_plot("tey_i0", "TEY / I0 (a.u.)", f"TEY (I0-norm) — {scan_label}",
            "tey_I0norm_curves.png", show_tey_i0)
single_plot("i0", "I0 (a.u.)", f"I0 — {scan_label}",
            "i0_curves.png", show_i0_curves)

# ---- Averaged RIXS map with PFY window (saved only) ----
fig, ax = plt.subplots(figsize=(9, 7))
mesh = draw_rixs_map(ax, window=(y_start, y_end))
fig.colorbar(mesh, ax=ax, label="Counts")
finish(fig, "avg_rixs_map.png", False)


# ==========================================================
# ==== SUMMARY + SHOW ======================================
# ==========================================================
shown = [name for name, flag in [
    ("Overview", show_overview),
    ("PFY (I0-norm)", show_i0_plot),
    ("PFY (area-norm)", show_area_plot),
    ("I0", show_i0_curves),
    ("TEY (raw)", show_tey_raw),
    ("TEY (I0-norm)", show_tey_i0),
] if flag]

i_lo, i_hi = window_indices(em_axis, y_start, y_end)
print_summary(window=(y_start, y_end), n_rows=i_hi - i_lo + 1, shown=shown, n_png=n_png)

if shown:
    plt.show()
