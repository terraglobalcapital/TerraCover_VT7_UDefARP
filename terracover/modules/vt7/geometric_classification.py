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
VT7 Vulnerability Classification and NRT Calculation

This module contains functions for:
- NRT (Negligible Risk Threshold) calculation
- Geometric classification of distance from the forest edge (benchmark model, as VT0007
  prescribes it)
- k-means classification of an empirical vulnerability surface (alternative models)

The two classifications differ because the surfaces do. Geometric intervals suit the
distribution of distance-from-edge; over an ETP they leave the least vulnerable classes empty or
holding too few pixels to estimate a relative frequency over, which in turn produces modeling
regions with no observed frequency at all. k-means partitions whatever distribution it is given
into exactly n_classes populated groups. The protocol requires the geometric classification for
the benchmark only.
"""

import os
import sys
import numpy as np
from osgeo import gdal

# matplotlib.pyplot is imported by _pyplot() inside nrt_calculation, the only
# function that draws. Importing it here pulled matplotlib (and, through pyplot,
# IPython) into every launcher tab that touches the VT7 package.


def _pyplot():
    """Import pyplot behind the headless Agg backend."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    return plt

# Enable GDAL exceptions for better error handling
gdal.UseExceptions()

try:
    from .utils import image_to_array, array_to_image, apply_mask_to_raster, replace_ref_system, raster_calculator, build_filename, pixel_size_meters
    from .terminology import BENCHMARK_DF, terms
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
    from terracover.modules.vt7.utils import image_to_array, array_to_image, apply_mask_to_raster, replace_ref_system, raster_calculator, build_filename, pixel_size_meters
    from terracover.modules.vt7.terminology import BENCHMARK_DF, terms


def nrt_calculation(in_fn, deforestation_hrp, mask, output_folder, project_name=None, version=None,
                    benchmark_type=BENCHMARK_DF):
    '''
    NRT calculation
    :param in_fn: map of distance from the forest edge in CAL
    :param deforestation_hrp: deforestation binary map in HRP (degradation map on an FCBM-DG run)
    :param mask: mask of the non-excluded jurisdiction (binary map)
    :param output_folder: folder to save PNG plots (required)
    :param project_name: Project name to prepend to output filenames (default: None)
    :param version: Version identifier to append to output filenames (default: None)
    :param benchmark_type: "deforestation" (default) or "degradation" — labels only; the histogram,
                           the 99.5th percentile and the NRT itself are identical either way
    :return: NRT: Negligible Risk Threshold
    '''
    plt = _pyplot()
    _t = terms(benchmark_type)

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
    # Use the true pixel size, not int(P): the bin width sets the distance histogram, whose 99.5th
    # percentile IS the NRT. int(30.0)==30 so nothing changes for 30 m/10 m UTM
    # inputs, but a 29.97 m raster used to bin at 29 and shift the NRT. Also rejects a degrees CRS,
    # which would make the whole metres-based analysis meaningless.
    bin_width = pixel_size_meters(in_ds, "geometric classification (NRT histogram)")
    # Calculate the histogram
    hist, bin_edges = np.histogram(distance_arr_masked_1d, bins=np.arange(distance_arr_masked_1d.min(),
                                                                            distance_arr_masked_1d.max() + bin_width,
                                                                          bin_width))
    plt.figure(figsize=(10, 6))
    plt.bar(bin_edges[:-1], hist, width=bin_width, align='edge')
    plt.xlabel('Distance from forest edge (m)')
    plt.ylabel(f'Frequency of {_t.lower} (pixels)')
    plt.title(f'Histogram of {_t.noun} Distance from Forest Edge')
    # save plot as png
    histogram_png_name = build_filename(f"01_BCM_Histogram_{_t.lower}_distance.png", project_name, version)
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
    plt.title(f'Cumulative Histogram of {_t.noun} Distance from Forest Edge')
    plt.legend(['NRT threshold', 'Below NRT', 'Above NRT'])

    # Add text annotation for NRT value
    plt.text(NRT, 0.5, f'NRT: {NRT}m',
                rotation=90, verticalalignment='center')

    # save plot as png
    cumulative_histogram_png_name = build_filename(f"02_BCM_Cumulative_histogram_{_t.lower}_distance.png", project_name, version)
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
        f.write(f"99.5 percent of the {_t.lower} experienced over the HRP has occurred.\n\n")
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

    # The lower limit of the highest class = spatial resolution (minimum distance without being in
    # non-forest). True pixel size, not int(P): LL feeds the geometric ratio r = (LL/UL)^(1/(n-1))
    # that sets every class boundary. int(30.0)==30 (no change for UTM 30 m); a 29.97 m raster used
    # to use 29.
    LL = pixel_size_meters(in_ds, "geometric classification (class boundaries)")

    # The upper limit of the lowest class = the Negligible Risk Threshold
    UL = NRT = int(NRT)
    n_classes = int(n_classes)

    # Number of classes within NRT (total classes - 1 for the class beyond NRT)
    n_classes_within_nrt = n_classes - 1

    # Guard the divisors before computing the geometric ratio (Python int division by zero raises).
    if UL == 0:
        raise ValueError("NRT (Negligible Risk Threshold) must be greater than 0")
    if n_classes_within_nrt == 0:
        raise ValueError("n_classes must be greater than 1")

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
    # ignore_cleanup_errors: a stray GDAL handle must not bury the real error.
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_folder:
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
def kmeans_classification_alternative(in_fn, n_classes, mask, fmask, out_fn, random_state=0):
    '''
    k-means classification of an alternative (empirical) vulnerability surface.

    VT0007 prescribes geometric intervals for the benchmark, where the surface being classified is
    distance from the forest edge and those intervals suit its distribution. An empirical
    vulnerability surface is not distributed that way: fixed geometric intervals over it leave the
    least vulnerable classes empty, or holding so few pixels that the relative frequency estimated
    over them is meaningless — and a class absent from the fitting phase but present in prediction
    then has no observed frequency at all. k-means partitions whatever distribution it is handed
    into exactly n_classes populated groups, which removes that failure at its source. The protocol
    does not require the alternative models to use the geometric classification.

    Class 1 is the least vulnerable and class n_classes the most, matching the benchmark's ordering,
    which the modeling-region encoding and the frequency table both rely on.

    :param in_fn: empirical vulnerability map (higher = more vulnerable)
    :param n_classes: number of classes to produce
    :param mask: mask of the non-excluded jurisdiction (binary map)
    :param fmask: mask of the forest areas (binary map)
    :param out_fn: output filename for the classified raster
    :param random_state: seed for k-means initialisation, fixed so a run is reproducible
    :return: None
    '''
    import tempfile
    from sklearn.cluster import KMeans

    print("=" * 60)
    print("Creating Alternative Vulnerability Map - k-means Classification")
    print("=" * 60)
    print(f"Input: {os.path.basename(in_fn)}")
    print(f"Number of classes: {n_classes}")

    n_classes = int(n_classes)

    # Convert in_fn to NumPy array
    in_ds = gdal.Open(in_fn)
    in_band = in_ds.GetRasterBand(1)
    arr = in_band.ReadAsArray()
    nodata = in_band.GetNoDataValue()

    # Everything below this point works on the arrays, and one path out of here raises.
    # On Windows an open dataset holds its file: these are read from the caller's
    # TemporaryDirectory, so a handle left behind turns ANY failure in this function into
    # a WinError 32 raised by the directory cleanup, with the real error buried under it
    # as a nested "During handling of the above exception". Close them as soon as their
    # array is in hand -- the paths, which is all the writes below need, stay valid.
    in_band = None
    in_ds = None

    # Masks first: k-means is fitted on the analysis domain, not on the whole raster.
    print("Applying jurisdiction and forest masks...")
    in_ds1 = gdal.Open(mask)
    in_band1 = in_ds1.GetRasterBand(1)
    mask_arr_jur = in_band1.ReadAsArray()
    in_band1 = None
    in_ds1 = None

    in_ds2 = gdal.Open(fmask)
    in_band2 = in_ds2.GetRasterBand(1)
    fmask_arr = in_band2.ReadAsArray()
    in_band2 = None
    in_ds2 = None

    domain = (mask_arr_jur == 1) & (fmask_arr == 1)

    # The ETP has to cover the analysis domain. VT7 derives that domain right here, from its own
    # FCBM and exclusions, while TerraChange masked the ETP using its copy of the same inputs --
    # and nothing links the two. A NoData ETP pixel inside the domain would be classified from a
    # meaningless value, so the pixel would enter the analysis carrying noise, or drop out of it
    # entirely, and two models would then be fitted on different domains with nothing on screen to
    # show for it.
    #
    # Changing the FCBM means regenerating the exclusions, the region files and the TerraChange
    # ETPs with it; this is where skipping one of those surfaces. Raising rather than warning is
    # the point: the inputs disagree, so the run's outputs are not valid to begin with.
    if nodata is not None:
        _orphans = int(np.count_nonzero(domain & (arr == nodata)))
        if _orphans:
            raise ValueError(
                f"kmeans_classification_alternative: the ETP has NoData on {_orphans:,} pixels "
                f"that are inside the analysis domain (non-excluded jurisdiction AND forest), "
                f"out of {int(np.count_nonzero(domain)):,}. Those pixels cannot be classified, so "
                f"this model would be fitted on a different domain from one whose ETP writes 0 "
                f"there instead, and the two would not be comparable.\n"
                f"  ETP:        {in_fn}\n"
                f"  mask:       {mask}\n"
                f"  forest:     {fmask}\n"
                f"The ETP and this domain come from different modules reading the same FCBM and "
                f"exclusions; a mismatch means they were regenerated out of step. Rebuild the "
                f"TerraChange ETPs against the current FCBM, exclusions and region files, or fix "
                f"whichever of those is stale."
            )

    values = arr[domain].astype(np.float64)
    if values.size < n_classes:
        raise ValueError(
            f"kmeans_classification_alternative: the analysis domain holds {values.size:,} pixels, "
            f"fewer than the {n_classes} classes requested. Check the masks and the ETP extent."
        )

    # Fit on a sample when the domain is large: the cut points of a 1-D partition are stable well
    # below the full population, and this keeps the step to seconds on a jurisdiction-sized raster.
    SAMPLE = 300_000
    rng = np.random.default_rng(random_state)
    fit_values = values if values.size <= SAMPLE else rng.choice(values, SAMPLE, replace=False)
    km = KMeans(n_clusters=n_classes, random_state=random_state, n_init=10)
    km.fit(fit_values.reshape(-1, 1))

    # Ascending centroids, so class 1 is the least vulnerable; cut points sit midway between them.
    centres = np.sort(km.cluster_centers_.ravel())
    cuts = (centres[:-1] + centres[1:]) / 2.0
    print(f"Class boundaries from k-means (on {fit_values.size:,} of {values.size:,} pixels):")
    print(f"  centroids {centres.min():.6f} .. {centres.max():.6f}")

    print("Classifying raster...")
    classes = np.digitize(values, cuts) + 1        # 1..n_classes, ascending vulnerability

    # 0 stays outside the domain and is turned into NoData by the masking step below.
    mask_arr = np.zeros(arr.shape, dtype=np.float64)
    mask_arr[domain] = classes

    occupancy = np.bincount(classes, minlength=n_classes + 1)[1:]
    empty = [int(i + 1) for i, c in enumerate(occupancy) if c == 0]
    print(f"  class sizes {int(occupancy.min()):,} .. {int(occupancy.max()):,} pixels"
          f"  (ratio {occupancy.max() / max(occupancy.min(), 1):,.1f}x)")
    if empty:
        # k-means should not leave a class empty; if it does, the surface is degenerate (for
        # instance heavily tied values) and the frequency table would inherit the same gap the
        # geometric classification used to produce.
        print(f"  WARNING: classes {empty} came out empty despite k-means; the vulnerability "
              f"surface may be degenerate (many tied values).")

    # Save classified raster to temporary file
    print("Saving alternative vulnerability map...")
    # ignore_cleanup_errors: a stray GDAL handle must not bury the real error.
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_folder:
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
