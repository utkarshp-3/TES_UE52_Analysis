#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat May 23 13:02:10 2026

@author: utkarshprakash
"""

"""
Interactive Diagonal PFY Integration for RIXS Maps

Features
--------
✓ Average multiple scans
✓ Diagonal PFY integration
✓ Adjustable diagonal width
✓ Square integration region
✓ Interactive sliders
✓ Real-time PFY updates
✓ Overlay integration region visualization
✓ I0 normalization
✓ Save button
✓ Save PFY + mask + PNG snapshot
✓ Hover mouse to read Counts values

"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
import os


# ==========================================================
# ================= USER INPUT =============================
# ==========================================================

folder_path = '/Users/utkarshprakash/Documents/Phd/Beamtime/Data/TES Beamtime/2026/May/Fe2S2/ProcessedData/Vertical'

start_xxx = int(input("Enter start scan number: "))
end_xxx   = int(input("Enter end scan number: "))

print("\n--- Initial Diagonal Integration Parameters ---")

diag_offset = float(input("Initial diagonal offset (eV): "))
diag_width  = 5.0

mono_min = float(input("Mono minimum for square region: "))
mono_max = float(input("Mono maximum for square region: "))


# ==========================================================
# ================= STORAGE ================================
# ==========================================================

all_counts = []
all_mono = []
all_emission = []
all_i0 = []

reference_shape = None


# ==========================================================
# ================= LOAD DATA ==============================
# ==========================================================

for xxx in range(start_xxx, end_xxx + 1):

    scan_file = f"scan{xxx}.npz"
    bld_file  = f"scan{xxx}_bld.npz"

    scan_path = os.path.join(folder_path, scan_file)
    bld_path  = os.path.join(folder_path, bld_file)

    try:

        # --------------------------------------------------
        # Load RIXS scan
        # --------------------------------------------------

        data = np.load(scan_path)

        mono     = data[data.files[0]]
        emission = data[data.files[1]]
        counts   = data[data.files[2]]

        data.close()

        # shape consistency check
        if reference_shape is None:
            reference_shape = counts.shape

        elif counts.shape != reference_shape:
            print(f"Skipping {scan_file}: shape mismatch")
            continue

        # --------------------------------------------------
        # Load beamline data
        # --------------------------------------------------

        bld = np.load(bld_path)

        i0     = bld[bld.files[0]]
        tey    = bld[bld.files[1]]
        diode1 = bld[bld.files[2]]
        sgm_en = bld[bld.files[3]]

        bld.close()

        # --------------------------------------------------
        # Store
        # --------------------------------------------------

        all_counts.append(counts)
        all_mono.append(mono)
        all_emission.append(emission)
        all_i0.append(i0)

        print(f"Loaded {scan_file}")

    except Exception as e:
        print(f"Error loading {scan_file}: {e}")


# ==========================================================
# ================= AVERAGING ==============================
# ==========================================================

if len(all_counts) == 0:
    raise RuntimeError("No valid scans loaded.")

all_counts = np.array(all_counts)

avg_counts = np.mean(all_counts, axis=0)
avg_mono   = np.mean(np.array(all_mono), axis=0)
avg_em     = np.mean(np.array(all_emission), axis=0)
avg_i0     = np.mean(np.array(all_i0), axis=0)

x_axis = avg_mono[0, :]
y_axis = avg_em[:, 0]


# ==========================================================
# ========= DIAGONAL PFY INTEGRATION FUNCTION ==============
# ==========================================================

def compute_diagonal_pfy(
    counts,
    mono,
    emission,
    diag_center,
    width,
    mono_start,
    mono_end,
    i0=None
):

    """
    Diagonal PFY integration.

    Integration follows:

        emission = mono + diag_center

    with finite width.
    """

    # ------------------------------------------------------
    # Diagonal coordinate
    # ------------------------------------------------------

    delta_map = emission - mono

    # ------------------------------------------------------
    # Diagonal strip
    # ------------------------------------------------------

    diag_mask = (
        (delta_map >= diag_center - width/2) &
        (delta_map <= diag_center + width/2)
    )

    # ------------------------------------------------------
    # Square region
    # ------------------------------------------------------

    emission_min = mono_start + diag_center
    emission_max = mono_end   + diag_center

    square_mask = (
        (mono >= mono_start) &
        (mono <= mono_end) &
        (emission >= emission_min) &
        (emission <= emission_max)
    )

    # ------------------------------------------------------
    # Final mask
    # ------------------------------------------------------

    mask = diag_mask & square_mask

    # ------------------------------------------------------
    # Apply mask
    # ------------------------------------------------------

    masked_counts = np.where(mask, counts, 0)

    # ------------------------------------------------------
    # Integrate
    # ------------------------------------------------------

    pfy = np.trapz(
        masked_counts,
        x=emission[:,0],
        axis=0
    )

    # ------------------------------------------------------
    # Normalize by I0
    # ------------------------------------------------------

    if i0 is not None:

        if len(i0) == len(pfy):

            pfy = pfy / i0

    return pfy, mask


# ==========================================================
# ================= INITIAL PFY ============================
# ==========================================================

initial_pfy, initial_mask = compute_diagonal_pfy(
    avg_counts,
    avg_mono,
    avg_em,
    diag_offset,
    diag_width,
    mono_min,
    mono_max,
    avg_i0
)

# area normalization
area = np.trapz(initial_pfy, x=x_axis)

if area != 0:
    initial_pfy = initial_pfy


# ==========================================================
# ================= FIGURE =================================
# ==========================================================

fig = plt.figure(figsize=(12,9))


# ==========================================================
# ================= RIXS MAP ===============================
# ==========================================================

ax_map = plt.axes([0.1, 0.35, 0.8, 0.55])

mesh = ax_map.pcolormesh(
    avg_mono,
    avg_em,
    avg_counts,
    shading='auto',
    cmap='gist_ncar'
)


# ==========================================================
# ======== SHOW COUNTS VALUE ON MOUSE HOVER ================
# ==========================================================

def format_coord(x, y):

    # nearest indices
    col = np.searchsorted(x_axis, x) - 1
    row = np.searchsorted(y_axis, y) - 1

    # bounds check
    if (
        0 <= row < avg_counts.shape[0]
        and
        0 <= col < avg_counts.shape[1]
    ):

        z = avg_counts[row, col]

        return (
            f"Mono={x:.3f} eV   "
            f"Emission={y:.3f} eV   "
            f"Counts={z:.3f}"
        )

    else:

        return (
            f"Mono={x:.3f} eV   "
            f"Emission={y:.3f} eV"
        )

ax_map.format_coord = format_coord


# overlay integration region
overlay = np.ma.masked_where(initial_mask == 0, initial_mask)

mask_plot = ax_map.pcolormesh(
    avg_mono,
    avg_em,
    overlay,
    shading='auto',
    cmap='Reds',
    alpha=0.35
)

cbar = plt.colorbar(mesh, ax=ax_map)
cbar.set_label("Counts")

ax_map.set_xlabel("Mono Energy (eV)")
ax_map.set_ylabel("Emission Energy (eV)")

ax_map.set_title(
    f"Interactive Diagonal PFY Integration\n"
    f"Scans {start_xxx}-{end_xxx}"
)


# ==========================================================
# ================= PFY PLOT ===============================
# ==========================================================

ax_pfy = plt.axes([0.1, 0.12, 0.8, 0.17])

pfy_line, = ax_pfy.plot(
    x_axis,
    initial_pfy,
    color='black',
    lw=2
)

ax_pfy.set_xlabel("Incident Energy (eV)")
ax_pfy.set_ylabel("Normalized PFY")

ax_pfy.grid(alpha=0.3)


# ==========================================================
# ================= SLIDERS ================================
# ==========================================================

slider_color = 'lightgoldenrodyellow'


# ----------------------------------------------------------
# Offset slider
# ----------------------------------------------------------

ax_offset = plt.axes(
    [0.15, 0.05, 0.65, 0.02],
    facecolor=slider_color
)

offset_slider = Slider(
    ax=ax_offset,
    label='Diagonal Offset',
    valmin=-20,
    valmax=20,
    valinit=diag_offset,
    valstep=0.1
)


# ----------------------------------------------------------
# Width slider
# ----------------------------------------------------------

ax_width = plt.axes(
    [0.15, 0.02, 0.65, 0.02],
    facecolor=slider_color
)

width_slider = Slider(
    ax=ax_width,
    label='Width (eV)',
    valmin=0.5,
    valmax=20,
    valinit=diag_width,
    valstep=0.1
)


# ----------------------------------------------------------
# Mono min slider
# ----------------------------------------------------------

ax_mono_min = plt.axes(
    [0.15, 0.08, 0.3, 0.02],
    facecolor=slider_color
)

mono_min_slider = Slider(
    ax=ax_mono_min,
    label='Mono Min',
    valmin=np.min(x_axis),
    valmax=np.max(x_axis),
    valinit=mono_min,
    valstep=0.1
)


# ----------------------------------------------------------
# Mono max slider
# ----------------------------------------------------------

ax_mono_max = plt.axes(
    [0.55, 0.08, 0.3, 0.02],
    facecolor=slider_color
)

mono_max_slider = Slider(
    ax=ax_mono_max,
    label='Mono Max',
    valmin=np.min(x_axis),
    valmax=np.max(x_axis),
    valinit=mono_max,
    valstep=0.1
)


# ==========================================================
# ================= UPDATE FUNCTION ========================
# ==========================================================

def update(val):

    diag_center = offset_slider.val
    width       = width_slider.val
    mono_start  = mono_min_slider.val
    mono_end    = mono_max_slider.val

    pfy, mask = compute_diagonal_pfy(
        avg_counts,
        avg_mono,
        avg_em,
        diag_center,
        width,
        mono_start,
        mono_end,
        avg_i0
    )

    # normalize
    area = np.trapz(pfy, x=x_axis)

    if area != 0:
        pfy = pfy

    # ------------------------------------------------------
    # Update PFY line
    # ------------------------------------------------------

    pfy_line.set_ydata(pfy)

    ax_pfy.relim()
    ax_pfy.autoscale_view()

    # ------------------------------------------------------
    # Update overlay
    # ------------------------------------------------------

    global mask_plot

    mask_plot.remove()

    new_overlay = np.ma.masked_where(mask == 0, mask)

    mask_plot = ax_map.pcolormesh(
        avg_mono,
        avg_em,
        new_overlay,
        shading='auto',
        cmap='Reds',
        alpha=0.35
    )

    fig.canvas.draw_idle()


# ==========================================================
# ================= CONNECT SLIDERS ========================
# ==========================================================

offset_slider.on_changed(update)
width_slider.on_changed(update)
mono_min_slider.on_changed(update)
mono_max_slider.on_changed(update)


# ==========================================================
# ================= SAVE BUTTON ============================
# ==========================================================

save_folder = os.path.join(
    folder_path,
    "interactive_diagonal_pfy"
)

os.makedirs(save_folder, exist_ok=True)


# ----------------------------------------------------------
# Save button
# ----------------------------------------------------------

ax_save = plt.axes([0.87, 0.015, 0.1, 0.05])

save_button = Button(
    ax=ax_save,
    label='Save Cut',
    color='lightblue',
    hovercolor='skyblue'
)


# ==========================================================
# ================= SAVE FUNCTION ==========================
# ==========================================================

def save_current_cut(event):

    diag_center = offset_slider.val
    width       = width_slider.val
    mono_start  = mono_min_slider.val
    mono_end    = mono_max_slider.val

    pfy, mask = compute_diagonal_pfy(
        avg_counts,
        avg_mono,
        avg_em,
        diag_center,
        width,
        mono_start,
        mono_end,
        avg_i0
    )

    # ------------------------------------------------------
    # Normalize PFY
    # ------------------------------------------------------

    area = np.trapz(pfy, x=x_axis)

    if area != 0:
        pfy_norm = pfy / area
    else:
        pfy_norm = pfy

    # ------------------------------------------------------
    # Filename
    # ------------------------------------------------------

    filename_base = (
        f"diagPFY_"
        f"offset_{diag_center:.2f}_"
        f"width_{width:.2f}_"
        f"mono_{mono_start:.2f}_{mono_end:.2f}"
    )

    # ------------------------------------------------------
    # Save PFY
    # ------------------------------------------------------

    pfy_filename = os.path.join(
        save_folder,
        filename_base + ".txt"
    )

    np.savetxt(
        pfy_filename,
        np.column_stack([x_axis, pfy_norm]),
        header=(
            "Incident_Energy(eV)    Normalized_Diagonal_PFY\n"
            f"Offset = {diag_center:.3f} eV\n"
            f"Width = {width:.3f} eV\n"
            f"MonoRange = {mono_start:.3f} - {mono_end:.3f} eV"
        )
    )

    # ------------------------------------------------------
    # Save mask
    # ------------------------------------------------------

    mask_filename = os.path.join(
        save_folder,
        filename_base + "_mask.txt"
    )

    np.savetxt(
        mask_filename,
        mask.astype(int)
    )

    # ------------------------------------------------------
    # Save figure
    # ------------------------------------------------------

    figure_filename = os.path.join(
        save_folder,
        filename_base + ".png"
    )

    fig.savefig(
        figure_filename,
        dpi=300,
        bbox_inches='tight'
    )

    print("\n====================================")
    print("Saved current diagonal PFY cut:")
    print(pfy_filename)
    print(mask_filename)
    print(figure_filename)
    print("====================================\n")


# connect button
save_button.on_clicked(save_current_cut)


# ==========================================================
# ================= SHOW ===================================
# ==========================================================

plt.show()