# coding=utf-8
# ------------------------------------------------------------------------
#
#   Copyright:          © Terra Global Capital. All rights reserved.
#   Author:             david.montoya@terraglobalcapital.com
#   Python version:     3.11
#   GDAL version:       3.10.3
#   Year:               2025
#
#   This code is proprietary and confidential.
#   Unauthorized copying or distribution is prohibited.
#
# ------------------------------------------------------------------------

"""
VT7 Geometric Classification and NRT Calculation

This module contains functions for:
- NRT (Negligible Risk Threshold) calculation
- Geometric classification (benchmark model)
- Alternative geometric classification
"""

import os
import sys
import numpy as np
from osgeo import gdal
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Enable GDAL exceptions for better error handling
gdal.UseExceptions()

try:
    from .utils import image_to_array, array_to_image, apply_mask_to_raster, replace_ref_system, raster_calculator, build_filename
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
    from terracover.modules.vt7.utils import image_to_array, array_to_image, apply_mask_to_raster, replace_ref_system, raster_calculator, build_filename


def nrt_calculation(in_fn, deforestation_hrp, mask, output_folder, project_name=None, version=None):
    '''
    NRT calculation
    :param in_fn: map of distance from the forest edge in CAL
    :param deforestation_hrp: deforestation binary map in HRP
    :param mask: mask of the non-excluded jurisdiction (binary map)
    :param output_folder: folder to save PNG plots (required)
    :param project_name: Project name to prepend to output filenames (default: None)
    :param version: Version identifier to append to output filenames (default: None)
    :return: NRT: Negligible Risk Threshold
    '''
    # Convert image to NumPy array
    distance_arr_cal = image_to_array(in_fn)
    deforestation_hrp_arr = image_to_array(deforestation_hrp)

    # Apply deforestation_hrp mask to mask
    # Where deforestation_hrp has valid data, keep mask value, else set to 0
    mask_arr = apply_mask_to_raster(mask, deforestation_hrp, outside_value=0)

    # Ensure output folder exists
    os.makedirs(output_folder, exist_ok=True)

    # Mask the distance arr within deforstation pixel and study area
    distance_arr_masked=distance_arr_cal*mask_arr*deforestation_hrp_arr

    ## Calculate the histogram
    # Flatten the distance_arr_masked and expect 0 for np.histogram function
    # The np.histogram is computed over the flattened array
    distance_arr_masked_1d = distance_arr_masked.flatten()
    distance_arr_masked_1d = distance_arr_masked_1d[distance_arr_masked_1d != 0]

    ## Calculate the histogram
    # Set up bin width as spatial resolution
    in_ds = gdal.Open(in_fn)
    P = in_ds.GetGeoTransform()[1]
    bin_width =int(P)
    # Calculate the histogram
    hist, bin_edges = np.histogram(distance_arr_masked_1d, bins=np.arange(distance_arr_masked_1d.min(),
                                                                            distance_arr_masked_1d.max() + bin_width,
                                                                          bin_width))
    plt.figure(figsize=(10, 6))
    plt.bar(bin_edges[:-1], hist, width=bin_width, align='edge')
    plt.xlabel('Distance from forest edge (m)')
    plt.ylabel('Frequency of deforestation (pixels)')
    plt.title('Histogram of Deforestation Distance from Forest Edge')
    # save plot as png
    histogram_png_name = build_filename("01_BCM_Histogram_deforestation_distance.png", project_name, version)
    histogram_png = os.path.join(output_folder, histogram_png_name)
    plt.savefig(histogram_png)
    plt.close()
    
    # Calculate the cumulative proportion
    # Normalize the histogram to get probability
    hist_normalized = hist / np.sum(hist)

    # Compute cumulative distribution
    cumulative_prop = np.cumsum(hist_normalized)

    # # Find the index cumulative proportion >= 0.995
    index_995 = np.argmax(cumulative_prop >= 0.995)

    # Get the bin edges for the NRT bin
    nrt_bin_start = bin_edges[index_995]
    nrt_bin_end = bin_edges[index_995 + 1]

    # Calculate the average of the NRT bin
    NRT = int((nrt_bin_start + nrt_bin_end) / 2)
    
    # Create a cumulative histogram
    plt.figure(figsize=(10, 6))

    # Plot bins before index_995 in blue
    plt.bar(bin_edges[:-1][:index_995], cumulative_prop[:index_995],
            width=bin_width, align='edge', color='blue', alpha=0.7)

    # Plot bins after index_995 in green
    plt.bar(bin_edges[:-1][index_995:], cumulative_prop[index_995:],
            width=bin_width, align='edge', color='green', alpha=0.7)

    # Plot vertical line at NRT value
    plt.axvline(x=NRT, color='red', linestyle='--', linewidth=2)

    plt.xlabel('Distance from forest edge (m)')
    plt.ylabel('Cumulative proportion')
    plt.title('Cumulative Histogram of Deforestation Distance from Forest Edge')
    plt.legend(['NRT threshold', 'Below NRT', 'Above NRT'])

    # Add text annotation for NRT value
    plt.text(NRT, 0.5, f'NRT: {NRT}m',
                rotation=90, verticalalignment='center')

    # save plot as png
    cumulative_histogram_png_name = build_filename("02_BCM_Cumulative_histogram_deforestation_distance.png", project_name, version)
    cumulative_histogram_png = os.path.join(output_folder, cumulative_histogram_png_name)
    plt.savefig(cumulative_histogram_png)
    plt.close()

    # Save NRT value to text file
    nrt_txt_name = build_filename("03_BCM_NRT_value.txt", project_name, version)
    nrt_txt = os.path.join(output_folder, nrt_txt_name)
    with open(nrt_txt, 'w') as f:
        f.write(f"Negligible Risk Threshold (NRT)\n")
        f.write(f"=" * 50 + "\n\n")
        f.write(f"The NRT is defined as the distance from forest edge at which\n")
        f.write(f"99.5 percent of the deforestation experienced over the HRP has occurred.\n\n")
        f.write(f"NRT value: {NRT} meters\n")
        f.write(f"NRT bin range: {nrt_bin_start:.2f} - {nrt_bin_end:.2f} meters\n")
        f.write(f"Cumulative proportion at NRT: {cumulative_prop[index_995]:.4f}\n")

    return NRT

# Create the Vulnerability Map
def geometric_classification(in_fn, out_fn, NRT, n_classes, nrt_txt=None):
    '''
    geometric classification
    :param in_fn: map of distance from the forest edge
    :param out_fn: output filename for the classified raster
    :param NRT: Negligible Risk Threshold
    :param n_classes: total number of classes (including class 1 for areas >= NRT)
    :param nrt_txt: optional path to NRT text file to append class boundaries table
    :return: None

    Example: if n_classes=30
    - Class 1: areas >= NRT (beyond NRT)
    - Classes 2-30: 29 classes within NRT, geometrically distributed
    '''
    import tempfile

    print("=" * 60)
    print("Creating Vulnerability Map - Geometric Classification")
    print("=" * 60)
    print(f"Input: {os.path.basename(in_fn)}")
    print(f"NRT: {NRT:.2f} meters")
    print(f"Number of classes: {n_classes}")

    # Convert in_fn to NumPy array
    in_ds = gdal.Open(in_fn)
    in_band = in_ds.GetRasterBand(1)
    arr = in_band.ReadAsArray()

    # The lower limit of the highest class = spatial resolution (minimum distance without being in non-forest)
    LL = int(in_ds.GetGeoTransform()[1])

    # The upper limit of the lowest class = the Negligible Risk Threshold
    UL = NRT = int(NRT)
    n_classes = int(n_classes)

    # Number of classes within NRT (total classes - 1 for the class beyond NRT)
    n_classes_within_nrt = n_classes - 1

    # Calculate common ratio (r) = (LL/UL)^(1/(n_classes-1))
    r = np.power(LL / UL, 1 / n_classes_within_nrt)
    print(f"Geometric ratio: {r:.6f}")

    # Calculate boundaries for each class within NRT
    # risk_class[i][0] = upper bound, risk_class[i][1] = lower bound
    class_array = np.array([[i, i + 1] for i in range(n_classes_within_nrt)])
    x = np.power(r, class_array)
    risk_class = np.multiply(UL, x)

    # Append class boundaries table to NRT text file if provided
    if nrt_txt is not None and os.path.exists(nrt_txt):
        with open(nrt_txt, 'a') as f:
            f.write(f"\n\nVulnerability Class Boundaries\n")
            f.write(f"=" * 50 + "\n")
            f.write(f"Number of classes: {n_classes}\n")
            f.write(f"Geometric ratio: {r:.6f}\n\n")
            f.write(f"Class|Upper limit (m)|Lower limit (m)\n")
            f.write(f"1|>= NRT|{NRT:.2f}\n")
            for i in range(n_classes_within_nrt):
                class_num = i + 2
                upper_bound = risk_class[i][0]
                lower_bound = risk_class[i][1]
                f.write(f"{class_num}|{upper_bound:.2f}|{lower_bound:.2f}\n")

    print("Classifying raster...")
    # Create result array
    mask_arr = arr.copy()

    # Areas beyond the NRT = class 1
    mask_arr[arr >= NRT] = 1

    # Classify areas within NRT (classes 2 to n_classes)
    # Process from highest class to lowest to avoid overwriting
    for i in range(n_classes_within_nrt - 1, -1, -1):
        upper_bound = risk_class[i][0]
        lower_bound = risk_class[i][1]
        mask_arr[(arr < upper_bound) & (arr >= lower_bound)] = i + 2

    # Save classified raster to temporary file
    # Use Byte (uint8) since vulnerability classes are 1-30 (well within uint8 range of 0-255)
    # Use 255 as nodata value (class values are 1-30, so 255 is safe)
    print("Saving vulnerability map...")
    with tempfile.TemporaryDirectory() as temp_folder:
        temp_out = os.path.join(temp_folder, "temp_classification.tif")
        array_to_image(in_fn, temp_out, mask_arr, gdal.GDT_Byte, 255)
        replace_ref_system(in_fn, temp_out)

        # Apply mask: where in_fn has data, keep out_fn values, otherwise set to nodata
        expression = "if(map1[1] != no_data, map2[1], no_data)"
        raster_calculator(
            input_files=[in_fn, temp_out],
            output_file=out_fn,
            expression=expression,
            out_dtype="uint8"
        )

    print(f"Vulnerability map saved: {os.path.basename(out_fn)}")
    print("=" * 60 + "\n")
    return None

# Create the Alternative Vulnerability Map
def geometric_classification_alternative(in_fn, n_classes, mask, fmask, out_fn):
    '''
    Geometric classification for alternative vulnerability map
    :param in_fn: Empirical vulnerability map [0.0,1.0] range
    :param n_classes: number of classes
    :param mask: mask of the non-excluded jurisdiction (binary map)
    :param fmask: mask of the forest areas (binary map)
    :param out_fn: output filename for the classified raster
    :return: None
    '''
    import tempfile

    print("=" * 60)
    print("Creating Alternative Vulnerability Map - Geometric Classification")
    print("=" * 60)
    print(f"Input: {os.path.basename(in_fn)}")
    print(f"Number of classes: {n_classes}")

    # Convert in_fn to NumPy array
    in_ds = gdal.Open(in_fn)
    in_band = in_ds.GetRasterBand(1)
    arr = in_band.ReadAsArray()

    # Always compute max from actual data to avoid stale/inherited GDAL metadata
    nodata = in_band.GetNoDataValue()
    if nodata is not None:
        valid_mask = arr != nodata
        max_value = float(np.max(arr[valid_mask])) if np.any(valid_mask) else float(np.max(arr))
    else:
        max_value = float(np.max(arr))

    # Rescale empirical vulnerability map to a [1.0–2.0] range
    arr_rescale = 1 + arr * 1 / max_value

    # The lower limit of the highest class = 1
    LL = int(1)

    # The upper limit of the lowest class = 2
    UL = int(2)
    n_classes = int(n_classes)

    # Calculate common ratio (r) = (LL/UL)^(1/n_classes)
    r = np.power(LL / UL, 1 / n_classes)
    print(f"Geometric ratio: {r:.6f}")

    # Generate raw geometric deltas (largest to smallest)
    raw_deltas = r ** np.arange(n_classes)

    # Normalize to sum to total range
    deltas = (UL - LL) * raw_deltas / raw_deltas.sum()

    # Create class edges by cumulative sum
    edges = LL + np.cumsum(np.insert(deltas, 0, 0))  # insert LL at start

    # Reshape to follow the same structure as the original upper:lower band
    risk_class = np.column_stack((edges[1:], edges[:-1]))  # upper first, then lower

    # Mask jurisdiction and forest area
    print("Applying jurisdiction and forest masks...")
    # Create jurisdiction mask array
    in_ds1 = gdal.Open(mask)
    in_band1 = in_ds1.GetRasterBand(1)
    mask_arr_jur = in_band1.ReadAsArray()

    # Create forest area array
    in_ds2 = gdal.Open(fmask)
    in_band2 = in_ds2.GetRasterBand(1)
    fmask_arr = in_band2.ReadAsArray()

    # Apply masks to rescaled array
    masked_values = arr_rescale * mask_arr_jur * fmask_arr

    # Create result array initialized with masked values
    mask_arr = masked_values.copy()

    print("Classifying raster...")
    # Classify all classes using a loop (from highest to lowest to avoid overwriting)
    # Process from class n_classes down to class 1
    for i in range(n_classes - 1, -1, -1):
        upper_bound = risk_class[i][0]
        lower_bound = risk_class[i][1]
        class_value = i + 1
        mask_arr[(masked_values < upper_bound) & (masked_values >= lower_bound)] = class_value

    # Save classified raster to temporary file
    print("Saving alternative vulnerability map...")
    with tempfile.TemporaryDirectory() as temp_folder:
        temp_out = os.path.join(temp_folder, "temp_classification.tif")
        array_to_image(in_fn, temp_out, mask_arr, gdal.GDT_Byte, 255)
        replace_ref_system(in_fn, temp_out)

        # Apply mask: where fmask has data, keep out_fn values, otherwise set to nodata
        expression = "if(map1[1] != no_data, map2[1], no_data)"
        raster_calculator(
            input_files=[fmask, temp_out],
            output_file=out_fn,
            expression=expression,
            out_dtype="uint8"
        )

    print(f"Alternative vulnerability map saved: {os.path.basename(out_fn)}")
    print("=" * 60 + "\n")
    return None

# Modeling Region Map
