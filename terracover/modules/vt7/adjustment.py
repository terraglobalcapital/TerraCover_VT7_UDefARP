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
VT7 Adjustment Ratio and Iterative Adjustment

This module contains functions for:
- Calculation of adjustment ratio (AR)
- Application of adjustment ratio to density arrays
- Iterative AR adjustment process
"""

import os
import sys
import numpy as np
from osgeo import gdal

# Enable GDAL exceptions for better error handling
gdal.UseExceptions()

try:
    from .utils import image_to_array, array_to_image, replace_ref_system, raster_calculator
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
    from terracover.modules.vt7.utils import image_to_array, array_to_image, replace_ref_system, raster_calculator


def calculate_adjustment_ratio_cnf(prediction_density_arr, deforestation_cnf=None, return_components=False, expected_deforestation=None):
    '''
    Calculate the Adjustment Ratio (AR) in CNF
    :param prediction_density_arr: modeled deforestation (MD)
    :param deforestation_cnf: deforestation binary map in cnf (optional if expected_deforestation is provided)
    :param return_components: if True, returns (AR, AD, MD) instead of just AR
    :param expected_deforestation: Expected deforestation in hectares (optional).
                                    If provided, AD will use this value instead of calculating from deforestation_cnf
    :return: AR or (AR, AD, MD) tuple if return_components=True
    '''

    # Sum up the pixels in the prediction density map. This is the modeled deforestation (MD).
    MD = np.sum(prediction_density_arr)

    # Calculate the Actual Deforestation (AD) during the confirmation period
    # Unless expected_deforestation is provided
    if expected_deforestation is not None:
        AD = expected_deforestation
    else:
        # Validate that deforestation_cnf is provided
        if deforestation_cnf is None:
            raise ValueError("Either 'deforestation_cnf' or 'expected_deforestation' must be provided")
        # Calculate areal_resolution_of_map_pixels and get nodata value
        in_ds5 = gdal.Open(deforestation_cnf)
        P1 = in_ds5.GetGeoTransform()[1]
        P2 = abs(in_ds5.GetGeoTransform()[5])
        areal_resolution_of_map_pixels = P1 * P2 / 10000

        # Get nodata value from raster band
        band = in_ds5.GetRasterBand(1)
        nodata_value = band.GetNoDataValue()

        # Convert deforestation_cnf to array
        arr5 = image_to_array(deforestation_cnf)

        # Create mask to exclude nodata values (typically 255 for uint8)
        # Only include pixels with value = 1 (deforestation)
        if nodata_value is not None:
            valid_mask = (arr5 == 1) & (arr5 != nodata_value)
        else:
            valid_mask = (arr5 == 1)

        # Apply mask: only calculate AD for valid deforestation pixels
        arr5_ha = np.where(valid_mask, arr5 * areal_resolution_of_map_pixels, 0)

        # Calculate the Actual Deforestation (AD) during the confirmation period
        AD = np.sum(arr5_ha)

    # AR = AD / MD
    AR = AD / MD

    if return_components:
        return AR, AD, MD
    else:
        return AR

# Create adjusted prediction density array
def adjusted_prediction_density_array(prediction_density_arr, risk30, AR):
    '''
    Create adjusted prediction density array
    :param prediction_density_arr:modeled deforestation (MD)
    :param risk30: risk30 image
    :param AR:Adjustment Ratio
    :return: adjusted_prediction_density_np_arr
    '''

    # Calculate the maximum density
    # Calculate areal_resolution_of_map_pixels
    in_ds4 = gdal.Open(risk30)
    P1 = in_ds4.GetGeoTransform()[1]
    P2 = abs(in_ds4.GetGeoTransform()[5])
    maximum_density = P1 * P2 / 10000

    # Adjusted_Prediction_Density_Map = AR x Prediction_Density _Map
    adjusted_prediction_density_arr=AR*prediction_density_arr

    # Reclassify all pixels greater than the maximum (e.g., 0.09) to be the maximum
    adjusted_prediction_density_arr[adjusted_prediction_density_arr > maximum_density] = maximum_density

    return adjusted_prediction_density_arr

# Create adjusted prediction density maps. Iterative adjustment to converge AR to 1.0
def iterative_ar_adjustment(prediction_density_arr, risk30, out_fn, log_fn, deforestation_cnf=None, max_iterations=5,
                             tolerance=1.00001, expected_deforestation=None, vp_years=None):
    '''
    Iteratively adjust the prediction density array until AR converges to 1.0
    Following VT7 methodology: applies AR accumulatively to previous iteration's result

    :param prediction_density_arr: initial prediction density array
    :param risk30: vulnerability map (risk30 image path)
    :param out_fn: output file path for the adjusted prediction density map
    :param log_fn: Path to the log file (required)
    :param deforestation_cnf: deforestation binary map in cnf (optional if expected_deforestation is provided)
    :param max_iterations: maximum number of iterations to avoid infinite loop (default: 5)
    :param tolerance: AR tolerance threshold (default: 1.00001)
    :param expected_deforestation: Expected deforestation in hectares (optional).
                                    If provided, AD will use this value instead of calculating from deforestation_cnf
    :param vp_years: Length of the Validity Period in years (optional, only for VP phase).
                     If provided, the output will be converted to annual deforestation rate by dividing by this value.
                     This follows VT0007 methodology for the Validity Period prediction phase.
                     For CNF phase, leave as None to output total density without annual conversion.
    :return: final adjusted prediction density array
    '''

    # Start with the original prediction density array
    current_density_arr = prediction_density_arr.copy()

    # Calculate initial AR with components
    AR, AD, MD = calculate_adjustment_ratio_cnf(current_density_arr, deforestation_cnf,
                                                 return_components=True,
                                                 expected_deforestation=expected_deforestation)

    # Initialize log list
    log_lines = []
    log_lines.append("VT7 Iterative AR Adjustment Log")
    log_lines.append("=" * 60)
    log_lines.append(f"Deforestation Map: {deforestation_cnf}")
    log_lines.append(f"Output File: {out_fn}")
    log_lines.append(f"Max Iterations: {max_iterations}")
    log_lines.append(f"Tolerance: {tolerance}")
    if expected_deforestation is not None:
        log_lines.append(f"Expected Deforestation: {expected_deforestation:,.2f} ha (AD will use this value)")
    if vp_years is not None:
        log_lines.append(f"VP Years: {vp_years} (output will be converted to annual rate)")
    log_lines.append("=" * 60)
    log_lines.append("")
    log_lines.append(f"Initial State:")
    log_lines.append(f"  MD (Modeled Deforestation):  {MD:,.2f} ha")
    if expected_deforestation is not None:
        log_lines.append(f"  AD (Expected Deforestation): {AD:,.2f} ha")
    else:
        log_lines.append(f"  AD (Actual Deforestation):   {AD:,.2f} ha")
    log_lines.append(f"  AR (Adjustment Ratio):       {AR:.6f}")
    log_lines.append("")

    iteration_count = 0
    inverse_tolerance = 1.0 / tolerance
    while (AR > tolerance or AR < inverse_tolerance) and iteration_count < max_iterations:
        iteration_count += 1

        # Apply AR to CURRENT array (accumulative per VT7 methodology)
        # VT7: "treat the result as the new prediction density map and repeat stages d)"
        current_density_arr = adjusted_prediction_density_array(current_density_arr, risk30, AR)

        # Recalculate AR based on the adjusted array
        AR, AD, MD = calculate_adjustment_ratio_cnf(current_density_arr, deforestation_cnf,
                                                     return_components=True,
                                                     expected_deforestation=expected_deforestation)

        # Log this iteration
        log_lines.append(f"Iteration {iteration_count}:")
        log_lines.append(f"  MD (Modeled Deforestation):  {MD:,.2f} ha")
        if expected_deforestation is not None:
            log_lines.append(f"  AD (Expected Deforestation): {AD:,.2f} ha")
        else:
            log_lines.append(f"  AD (Actual Deforestation):   {AD:,.2f} ha")
        log_lines.append(f"  AR (Adjustment Ratio):       {AR:.6f}")
        log_lines.append("")

    # Add final summary
    log_lines.append("=" * 60)
    log_lines.append(f"Final Results:")
    log_lines.append(f"  Total Iterations: {iteration_count}")
    log_lines.append(f"  Final AR: {AR:.6f}")
    converged = inverse_tolerance <= AR <= tolerance
    log_lines.append(f"  Converged: {'Yes' if converged else 'No (max iterations reached)'}")

    # Convert to annual rate only if vp_years is provided (VP phase only, not CNF)
    # Following Verra's original code: CNF uses adjusted_prediction_density_map (no division)
    # VP uses adjusted_prediction_density_map_annual (with division by time/vp_years)
    if vp_years is not None and vp_years > 0:
        output_density_arr = current_density_arr / vp_years
        log_lines.append(f"  Annual Conversion: Divided by {vp_years} years")
        log_lines.append(f"  Output Type: Annual deforestation rate (ha/year per pixel)")
    else:
        output_density_arr = current_density_arr
        log_lines.append(f"  Annual Conversion: None (CNF phase)")
        log_lines.append(f"  Output Type: Total deforestation density (ha per pixel)")
    log_lines.append("=" * 60)

    # Write log file
    with open(log_fn, 'w') as f:
        f.write('\n'.join(log_lines))

    # Save the final adjusted array to temporary file, then apply mask
    import tempfile
    with tempfile.TemporaryDirectory() as temp_folder:
        temp_out = os.path.join(temp_folder, "temp_adjusted_density.tif")
        array_to_image(risk30, temp_out, output_density_arr, gdal.GDT_Float32, -1)
        replace_ref_system(risk30, temp_out)

        # Apply mask: where risk30 has data, keep adjusted density values, otherwise set to nodata
        expression = "if(map1[1] != no_data, map2[1], no_data)"
        raster_calculator(
            input_files=[risk30, temp_out],
            output_file=out_fn,
            expression=expression,
            out_dtype="float32"
        )

    return None

# Model Evaluation - VT7
