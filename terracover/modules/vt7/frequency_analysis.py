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
VT7 Frequency Analysis and Tabulation

This module contains functions for:
- Tabulation of bin IDs with administrative divisions
- Substitution of relative frequencies for modeling regions missing from the fitting phase
- Creation of relative frequency tables
- Creation of fit density maps

A modeling region is a vulnerability zone crossed with an administrative division, so one can be
missing from the fitting phase for two different reasons, and `calculate_missing_bins_rf` treats
them differently: where the zone itself is present in other divisions the bin takes that zone's
area-weighted average, and where the whole zone is absent its frequency is unknown and is
interpolated along the vulnerability gradient. See that function for why a zero is not a
conservative substitute.
"""

import os
import sys
import numpy as np
from osgeo import gdal
import pandas as pd

# Enable GDAL exceptions for better error handling
gdal.UseExceptions()

try:
    from .utils import array_to_image, raster_calculator
    from .terminology import BENCHMARK_DF, terms, frequency_columns, align_frequency_columns
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
    from terracover.modules.vt7.utils import array_to_image, raster_calculator
    from terracover.modules.vt7.terminology import BENCHMARK_DF, terms, frequency_columns, align_frequency_columns


def tabulation_bin_id(risk30, municipality, out_fn1):
    """
    This function is to create fitting modeling region array(tabulation_bin_id_masked)
    and fitting modeling region map(tabulation_bin_image)
    :param risk30: The 30-class vulnerability map for the CAL/HRP
    :param municipality: Subdivision image
    :param out_fn1: user input
    :return: tabulation_bin_id_masked: tabulation bin id array in CAL/HRP
    """
    print("=" * 60)
    print("Creating Modeling Regions Map")
    print("=" * 60)
    print(f"Combining vulnerability classes with administrative divisions...")

    # Read risk30 raster and get nodata value
    ds1 = gdal.Open(risk30)
    band1 = ds1.GetRasterBand(1)
    nodata_risk30 = band1.GetNoDataValue()
    arr1 = band1.ReadAsArray().astype(np.int64)
    ds1 = None

    # Read municipality raster and get nodata value
    ds2 = gdal.Open(municipality)
    band2 = ds2.GetRasterBand(1)
    nodata_municipality = band2.GetNoDataValue()
    arr2 = band2.ReadAsArray().astype(np.int64)
    ds2 = None

    # Create comprehensive mask that excludes:
    # 1. risk30 <= 0 (no vulnerability)
    # 2. risk30 nodata values
    # 3. municipality nodata values
    mask_arr_HRP = np.ones(arr1.shape, dtype=np.int64)

    # Exclude risk30 <= 0
    mask_arr_HRP = np.where(arr1 > 0, mask_arr_HRP, 0)

    # Exclude risk30 nodata
    if nodata_risk30 is not None:
        mask_arr_HRP = np.where(arr1 != nodata_risk30, mask_arr_HRP, 0)

    # Exclude municipality nodata
    if nodata_municipality is not None:
        mask_arr_HRP = np.where(arr2 != nodata_municipality, mask_arr_HRP, 0)

    # Guard the base-1000 modeling-region encoding. bin_id = risk*1000 + admin,
    # decoded downstream as risk = bin_id // 1000 (lines ~187, ~190). That only holds while admin
    # < 1000: with >= 1000 divisions the ids collide -- risk=1,admin=1002 and risk=2,admin=2 both
    # become 2002 -- and two distinct modeling regions would silently merge, corrupting their
    # deforestation totals. admin_divisions_to_raster assigns consecutive ids from 2, so a
    # departmental jurisdiction (dozens of divisions) is far under the limit; a national one with
    # >= 1000 divisions needs a wider multiplier here AND in the two // 1000 decoders. Fail clearly
    # rather than merge regions in silence.
    valid_admin = arr2[mask_arr_HRP == 1]
    if valid_admin.size and int(valid_admin.max()) >= 1000:
        raise ValueError(
            f"frequency_analysis: administrative division id {int(valid_admin.max())} does not fit "
            f"the base-1000 modeling-region encoding (vulnerability_class * 1000 + admin_id): ids "
            f">= 1000 collide with a higher vulnerability class, merging distinct regions. This "
            f"jurisdiction has too many divisions for the current encoding -- widen the multiplier "
            f"here and in the two '// 1000' decoders."
        )

    # Calculate tabulation bin id with mask using int64 arithmetic to prevent overflow
    # Formula: (vulnerability_class * 1000 + admin_division) * mask
    tabulation_bin_id_masked = (arr1 * 1000 + arr2) * mask_arr_HRP

    # Convert the array to signed 32-bit integer (int32) data type
    # Note: int32 is required to store values up to ~2 billion
    # Expected range: 1,000 to ~30,999 (well within int32 range)
    tabulation_bin_id_masked = tabulation_bin_id_masked.astype(np.int32)

    # Create the final image using tabulation_bin_image function
    # Use 0 as nodata value (IDs start from 1000, so 0 is safe)
    array_to_image(risk30, out_fn1, tabulation_bin_id_masked, gdal.GDT_Int32, 0)

    # Count unique modeling regions (excluding 0)
    unique_bins = np.unique(tabulation_bin_id_masked[tabulation_bin_id_masked != 0])
    print(f"Number of modeling regions created: {len(unique_bins)}")
    print(f"Modeling regions map saved: {os.path.basename(out_fn1)}")
    print("=" * 60 + "\n")

    return tabulation_bin_id_masked

# Handle Missing Bins in Prediction Phase
def _interpolate_absent_zones(fitting_df, absent_zones, average_col):
    """Substituted relative frequency for vulnerability zones with no fitting data at all.

    The zones are an ordered sequence — zone 1 least vulnerable, zone 30 most — and the relative
    frequency rises along it, so the populated neighbours of an absent zone bound what it can
    plausibly be. For each absent zone:

    - Between two populated zones: linear interpolation on the zone index between the nearest
      populated zone below and the nearest above.
    - Below the lowest populated zone: that zone's frequency. It is the defensible upper bound —
      a less vulnerable zone should not be allocated more than the least vulnerable one observed.
    - Above the highest populated zone: symmetrically, that zone's frequency.

    Returns a list of (zone, value, basis) so the caller can report each substitution.
    """
    zone_freq = (fitting_df.assign(_t=fitting_df['Area of the Bin(pixel)'] * fitting_df[average_col])
                 .groupby('v_zone')
                 .apply(lambda g: g['_t'].sum() / g['Area of the Bin(pixel)'].sum(),
                        include_groups=False))
    populated = sorted(zone_freq.index)
    if not populated:
        raise ValueError("The fitting frequency table holds no vulnerability zone at all; "
                         "a substituted frequency cannot be derived from it.")

    out = []
    for zone in absent_zones:
        below = [z for z in populated if z < zone]
        above = [z for z in populated if z > zone]
        if below and above:
            lo, hi = below[-1], above[0]
            f_lo, f_hi = float(zone_freq[lo]), float(zone_freq[hi])
            w = (zone - lo) / (hi - lo)
            value = f_lo + w * (f_hi - f_lo)
            basis = f"interpolation between zones {lo} ({f_lo:.6f}) and {hi} ({f_hi:.6f})"
        elif below:
            lo = below[-1]
            value = float(zone_freq[lo])
            basis = f"the frequency of zone {lo}, the highest populated zone below it"
        else:
            hi = above[0]
            value = float(zone_freq[hi])
            basis = f"the frequency of zone {hi}, the lowest populated zone above it"
        out.append((zone, value, basis))
    return out


def calculate_missing_bins_rf(fitting_frequency_df, prediction_modeling_regions_array, fitting_frequency_table_path,
                              benchmark_type=BENCHMARK_DF):
    '''
    If one or more empty bins are found in prediction phase, compute the weighted average of
    relative frequencies for missing bins and update the frequency table.

    This is applied when modeling regions exist in the Prediction phase but not in the Fitting phase.
    A modeling region is a vulnerability zone crossed with an administrative division, so a region
    can be missing for two quite different reasons, and the two are NOT treated alike:

    1. The zone IS present in fitting, in other divisions. The bin takes the area-weighted average
       of that zone — a pooled relative frequency, pooled at the level of the vulnerability zone.
       The zone is the stratum the model attributes risk to; the division only subdivides it, so
       falling back to the stratum uses the information the model considers relevant. This is the
       normal case and the one that has actually occurred.

    2. The zone is ABSENT from fitting altogether. The bin is currently assigned 0.

    On case 2, note carefully what an absent zone does and does not mean. It does NOT mean the zone
    had no change: a zone that existed with no change appears in the table with an average of 0.
    Absence means the zone had no pixels at all — typically because the classification is recomputed
    per phase and the forest geometry moved (e.g. v_zone=1 appears in VP but never existed in HRP as
    forest area contracted). Its relative frequency is therefore UNKNOWN, not observed to be zero,
    and 0 is a placeholder rather than a conservative estimate. Two consequences follow:

    - The iterative AR adjustment cannot repair it. The adjustment is multiplicative, so a pixel at
      0 stays at 0 however many iterations run; the AR reconciles the aggregate quantity but cannot
      allocate any of it to those pixels.
    - 0 is not neutral. It asserts no risk in a zone that may be more vulnerable than zones that
      did receive an allocation.

    Case 2 is therefore resolved by interpolating between the neighbouring populated zones, falling
    back to the nearest populated zone at either end of the sequence: this preserves the monotonic
    vulnerability gradient and yields a positive value the AR can scale. See
    `_interpolate_absent_zones`. Every substitution is reported on stdout, with the basis used, so
    that it can be recorded in the model documentation and cannot pass silently.

    The reasoning and the measurements behind this rule are in
    docs/VT7_Absent_Vulnerability_Zones_Interpolation.md.

    Assigning 0 was the previous behaviour and is deliberately no longer reachable: it is not a
    conservative estimate of an unknown frequency, and leaving it available as an option would
    invite the same defect back into a later run.

    :param fitting_frequency_df: DataFrame with relative frequency table from fitting phase
    :param prediction_modeling_regions_array: Array of modeling region IDs from prediction phase
    :param fitting_frequency_table_path: Path to the fitting frequency table Excel file (will be backed up and updated)
    :param benchmark_type: "deforestation" (default) or "degradation" — picks the column vocabulary
    :return: Updated frequency table DataFrame with missing bins filled
    '''
    _t = terms(benchmark_type)
    total_col, average_col = frequency_columns(benchmark_type)
    # A fitting table written by the other benchmark (or before this flag existed) names its
    # columns the other way; realign before indexing them by name.
    fitting_frequency_df = align_frequency_columns(fitting_frequency_df, benchmark_type)

    # Get unique IDs from fitting phase and prediction phase
    fitting_ids = set(fitting_frequency_df['ID'].values)
    prediction_ids = set(np.unique(prediction_modeling_regions_array[prediction_modeling_regions_array != 0]))

    # Find IDs that exist in prediction but not in fitting
    id_difference = prediction_ids - fitting_ids

    # If no missing bins, return original dataframe
    if len(id_difference) == 0:
        print("No missing bins found. Frequency table unchanged.")
        return fitting_frequency_df

    print(f"Found {len(id_difference)} missing bins in prediction phase. Calculating weighted averages...")

    # Convert to list for processing
    id_difference = list(id_difference)

    # Convert modeling region ids to vulnerability zone id
    df = fitting_frequency_df.copy()
    df['v_zone'] = (df['ID'] // 1000).astype(int)

    # Convert missing bin ids to vulnerability zone id
    missing_v_zone = [x // 1000 for x in id_difference]

    # Identify v_zones that exist in fitting phase
    fitting_v_zones = set(df['v_zone'].values)

    # Identify missing v_zones (v_zones in prediction but not in fitting)
    missing_v_zones_set = set(missing_v_zone) - fitting_v_zones

    # Reported in full where the substitution happens, below; "(no historical change)" used to be
    # claimed here, which is wrong — see the docstring on what an absent zone actually means.
    if missing_v_zones_set:
        print(f"  {len(missing_v_zones_set)} vulnerability zone(s) absent from the fitting table: "
              f"{sorted(missing_v_zones_set)}")

    # Select rows from the same vulnerability zones as missing bins
    filtered_df = df[df['v_zone'].isin(missing_v_zone)].copy()

    # Calculate the total for the weighted average
    filtered_df[total_col] = filtered_df['Area of the Bin(pixel)'] * filtered_df[average_col]

    # Group by vulnerability zone and sum area and weighted relative frequency
    aggregated_df = filtered_df.groupby('v_zone')[[total_col, 'Area of the Bin(pixel)']].sum().reset_index()

    # Calculate the average for each vulnerability zone
    aggregated_df[average_col] = aggregated_df[total_col] / aggregated_df['Area of the Bin(pixel)']

    # Create dataframe for missing IDs
    id_difference_df = pd.DataFrame(id_difference, columns=['ID'])
    id_difference_df['v_zone'] = missing_v_zone

    # Create missing bins dataframe by merging with aggregated vulnerability zone data
    missing_bins_df = pd.merge(id_difference_df, aggregated_df, on='v_zone', how='left')

    # Case 2 of the docstring: the whole zone is absent from fitting, so the merge above found
    # nothing and the average is NaN. The frequency is unknown, and the substitution rule is the
    # frequency is unknown, and is substituted by interpolation along the vulnerability gradient.
    nan_mask = missing_bins_df[average_col].isna()
    nan_count = int(nan_mask.sum())
    if nan_count > 0:
        absent_zones = sorted(set(missing_bins_df.loc[nan_mask, 'v_zone']))
        for zone, value, basis in _interpolate_absent_zones(df, absent_zones, average_col):
            missing_bins_df.loc[missing_bins_df['v_zone'] == zone, average_col] = value
            print(f"  Zone {zone} is absent from the fitting table: assigned "
                  f"{average_col} = {value:.6f} by {basis}.")
        # Area and total are genuinely unknown for an absent zone; only the average is substituted.
        missing_bins_df[total_col] = missing_bins_df[total_col].fillna(0)
        missing_bins_df['Area of the Bin(pixel)'] = (
            missing_bins_df['Area of the Bin(pixel)'].fillna(0))
        print(f"  Report these {nan_count} substituted bin(s) (zones {absent_zones}) and their "
              f"area in the model documentation.")

    # The ordinary case: the zone was present and the bin took its area-weighted average.
    pooled_count = int(len(missing_bins_df) - nan_count)
    if pooled_count > 0:
        print(f"  {pooled_count} bin(s) took the pooled area-weighted average of their own "
              f"vulnerability zone (the zone was present in fitting).")

    # Drop v_zone column from missing bins (keep only the needed columns)
    missing_bins_df = missing_bins_df[['ID', total_col, 'Area of the Bin(pixel)', average_col]]

    # Insert missing bins dataframe back to original dataframe
    df_new = pd.concat([df.drop('v_zone', axis=1), missing_bins_df], ignore_index=True)

    # Sort by ID
    df_new = df_new.sort_values(by=['ID'], ascending=True).reset_index(drop=True)

    # Backup original file and save updated table
    import shutil
    backup_path = fitting_frequency_table_path.replace('.xlsx', '_orig.xlsx')
    if not os.path.exists(backup_path):  # Only backup if not already backed up
        shutil.copyfile(fitting_frequency_table_path, backup_path)
        print(f"Original frequency table backed up to: {backup_path}")

    # Save updated table to Excel with formatting
    with pd.ExcelWriter(fitting_frequency_table_path, engine='openpyxl') as writer:
        df_new.to_excel(writer, index=False, sheet_name='Relative Frequency')

        worksheet = writer.sheets['Relative Frequency']

        # Apply number formatting
        for row in range(2, len(df_new) + 2):
            # Total <noun>(pixel) - column 2
            cell_b = worksheet.cell(row=row, column=2)
            if isinstance(cell_b.value, (int, float)):
                cell_b.number_format = '#,##0'

            # Area of the Bin(pixel) - column 3
            cell_c = worksheet.cell(row=row, column=3)
            if isinstance(cell_c.value, (int, float)):
                cell_c.number_format = '#,##0'

            # Average <noun>(pixel) - column 4
            cell_d = worksheet.cell(row=row, column=4)
            if isinstance(cell_d.value, (int, float)):
                cell_d.number_format = '0.00000'

        # Embed provenance: a 'Parameters' sheet with the run arguments.
        try:
            from terracover.core.provenance import write_parameters_sheet
            _wb = writer.book
            if not any(s in _wb.sheetnames for s in ("Parameters", "Arguments")):
                _params = [("module", "VT7 Frequency Analysis")] + [
                    (k, v) for k, v in {
                        "function": "calculate_missing_bins_rf",
                        "benchmark_type": _t.benchmark_type,
                        "fitting_frequency_table_path": str(fitting_frequency_table_path),
                        "backup_path": str(backup_path),
                        "num_missing_bins": int(len(id_difference)),
                    }.items()
                ]
                write_parameters_sheet(_wb, _params)
        except Exception:
            pass

    print(f"Frequency table updated with {len(id_difference)} missing bins.")

    return df_new

# Create Relative Frequency Table
def create_relative_frequency_table(tabulation_bin_id_masked, deforestation_hrp, xlsx_name, map_output_path=None,
                                    benchmark_type=BENCHMARK_DF):
    """
    Create relative frequency table and optionally a raster map
    :param tabulation_bin_id_masked: array with id and the total per bin
    :param deforestation_hrp: change map during the CAL/HRP (path to raster file); the degradation
                              map on an FCBM-DG run
    :param xlsx_name: output Excel file path
    :param map_output_path: optional path for output relative frequency raster map (default: None, no map created)
    :param benchmark_type: "deforestation" (default) or "degradation" — picks the column vocabulary
    :return: merged_df: relative frequency dataframe
    """
    import tempfile

    _t = terms(benchmark_type)
    total_col, average_col = frequency_columns(benchmark_type)

    print("=" * 60)
    print("Creating Relative Frequency Table")
    print("=" * 60)
    print(f"Analyzing {_t.lower} within modeling regions...")

    # Calculate array area of the bin [integer] (in pixels) for Col3 using np.unique and counts function, excluding 0
    unique, counts = np.unique(tabulation_bin_id_masked[tabulation_bin_id_masked != 0], return_counts=True)
    # Convert to array
    arr_counts = np.asarray((unique, counts)).T

    # Read deforestation raster and get nodata value
    ds = gdal.Open(deforestation_hrp)
    band = ds.GetRasterBand(1)
    nodata_value = band.GetNoDataValue()
    arr3 = band.ReadAsArray()
    ds = None

    # Create mask to exclude nodata pixels
    if nodata_value is not None:
        valid_mask = (arr3 != nodata_value) & (arr3 != 0)
    else:
        valid_mask = (arr3 != 0)

    # Apply mask: only process valid deforestation pixels (value = 1, excluding nodata)
    deforestation_within_bin = np.where(valid_mask, tabulation_bin_id_masked * arr3, 0)

    # Use np.unique to counts total deforestation in each bin
    unique1, counts1 = np.unique(deforestation_within_bin[deforestation_within_bin != 0], return_counts=True)
    # Convert to array
    arr_counts_deforestion = np.asarray((unique1, counts1)).T

    # Create pandas DataFrames
    df1 = pd.DataFrame(arr_counts_deforestion, columns=['ID', total_col])
    df2 = pd.DataFrame(arr_counts, columns=['ID', 'Area of the Bin(pixel)'])

    # Merge the two DataFrames based on the 'id' column using an outer join to include all rows from both DataFrames
    merged_df = pd.merge(df1, df2, on='ID', how='outer').fillna(0)

    # Calculate the average = total / Bin Area. A bin with 0 area (present in the change counts but
    # not the bin counts after the outer join) has no average -> 0, instead of the inf that
    # dividing by 0 would give.
    _bin_area = merged_df.iloc[:, 2].astype(float)
    merged_df[average_col] = (
        merged_df.iloc[:, 1].astype(float) / _bin_area.replace(0, np.nan)
    ).fillna(0.0)

    # Sort the DataFrame based on the 'ID'
    merged_df = merged_df.sort_values(by='ID')

    # Reset the index to have consecutive integer indices
    merged_df = merged_df.reset_index(drop=True)

    print(f"Frequency table created with {len(merged_df)} regions")
    print(f"Saving frequency table Excel: {os.path.basename(xlsx_name)}")

    # Save to Excel with formatting
    excel_file_path = xlsx_name if xlsx_name.endswith('.xlsx') else xlsx_name.replace('.csv', '.xlsx')

    with pd.ExcelWriter(excel_file_path, engine='openpyxl') as writer:
        merged_df.to_excel(writer, index=False, sheet_name='Relative Frequency')

        # Get the worksheet to apply formatting
        worksheet = writer.sheets['Relative Frequency']

        # Set column widths (in pixels: 55, 170, 140, 190)
        # Note: openpyxl uses character width units, approximate conversion: pixels / 7
        worksheet.column_dimensions['A'].width = 55 / 7  # ~7.86 characters
        worksheet.column_dimensions['B'].width = 170 / 7  # ~24.29 characters
        worksheet.column_dimensions['C'].width = 140 / 7  # ~20 characters
        worksheet.column_dimensions['D'].width = 190 / 7  # ~27.14 characters

        # Apply number formatting to each column
        for row in range(2, len(merged_df) + 2):  # Start from row 2 (skip header)
            # ID column - no formatting needed (integer)

            # Total <noun>(pixel) - column 2: comma separator, no decimals
            cell_b = worksheet.cell(row=row, column=2)
            if isinstance(cell_b.value, (int, float)):
                cell_b.number_format = '#,##0'

            # Area of the Bin(pixel) - column 3: comma separator, no decimals
            cell_c = worksheet.cell(row=row, column=3)
            if isinstance(cell_c.value, (int, float)):
                cell_c.number_format = '#,##0'

            # Average <noun>(pixel) - column 4: 5 decimals
            cell_d = worksheet.cell(row=row, column=4)
            if isinstance(cell_d.value, (int, float)):
                cell_d.number_format = '0.00000'

        # Embed provenance: a 'Parameters' sheet with the run arguments.
        try:
            from terracover.core.provenance import write_parameters_sheet
            _wb = writer.book
            if not any(s in _wb.sheetnames for s in ("Parameters", "Arguments")):
                _params = [("module", "VT7 Frequency Analysis")] + [
                    (k, v) for k, v in {
                        "function": "create_relative_frequency_table",
                        "benchmark_type": _t.benchmark_type,
                        "deforestation_hrp": str(deforestation_hrp),
                        "xlsx_name": str(xlsx_name),
                        "excel_file_path": str(excel_file_path),
                        "map_output_path": str(map_output_path) if map_output_path is not None else None,
                        "num_regions": int(len(merged_df)),
                    }.items()
                ]
                write_parameters_sheet(_wb, _params)
        except Exception:
            pass

    # Create relative frequency raster map if output path is provided
    if map_output_path is not None:
        print(f"Creating relative frequency map: {os.path.basename(map_output_path)}")
        # Create a copy of tabulation_bin_id_masked to map IDs to relative frequency values
        relative_frequency_map = tabulation_bin_id_masked.copy().astype(np.float32)

        # Insert index=0 row for background (ID=0)
        new_row = pd.DataFrame({'ID': [0], total_col: [0],
                                'Area of the Bin(pixel)': [0], average_col: [0]})
        merged_df_with_zero = pd.concat([new_row, merged_df]).reset_index(drop=True)

        # Using numpy.searchsorted() to map IDs to relative frequency values
        df_sorted = merged_df_with_zero.sort_values('ID')
        sorted_indices = df_sorted['ID'].searchsorted(tabulation_bin_id_masked)
        relative_frequency_map[:] = df_sorted[average_col].values[sorted_indices]

        # Save relative frequency map to temporary file, then apply mask
        # ignore_cleanup_errors: a stray GDAL handle must not bury the real error.
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_folder:
            temp_out = os.path.join(temp_folder, "temp_relative_frequency.tif")
            array_to_image(deforestation_hrp, temp_out, relative_frequency_map, gdal.GDT_Float32, -1)

            # Apply mask: where deforestation_hrp has data, keep relative frequency values, otherwise set to nodata
            expression = "if(map1[1] != no_data, map2[1], no_data)"
            raster_calculator(
                input_files=[deforestation_hrp, temp_out],
                output_file=map_output_path,
                expression=expression,
                out_dtype="float32"
            )

    print("=" * 60 + "\n")
    return merged_df

# Create the Fitting Density Map
def create_fit_density_map(risk30, tabulation_bin_id_masked, merged_df, out_fn2=None,
                           benchmark_type=BENCHMARK_DF):
    '''
    Create the fitting density map, this function used for fitting phase (CAL and HRP)
    :param risk30: the 30-class vulnerability map for the CAL/HRP
    :param tabulation_bin_id_masked: array for tabulation bin id in fitting Phase
    :param merged_df: relative frequency dataframe
    :param out_fn2: optional output file path
    :param benchmark_type: "deforestation" (default) or "degradation" — picks the column vocabulary
    :return:
    '''
    import tempfile

    total_col, average_col = frequency_columns(benchmark_type)
    # Tolerate a table that speaks the other vocabulary (an older CAL/HRP run, or the other
    # benchmark): the columns below are indexed by name.
    merged_df = align_frequency_columns(merged_df, benchmark_type)

    print("=" * 60)
    print("Creating Fitting/Prediction Density Map")
    print("=" * 60)

    # Insert index=0 row into first row of merged_df DataFrame
    new_row = pd.DataFrame({'ID': [0], total_col: [0], 'Area of the Bin(pixel)': [0],
                            average_col: [0]})
    merged_df = pd.concat([new_row, merged_df]).reset_index(drop=True)

    # Using numpy.searchsorted() to assign values to 'id'
    df_sorted = merged_df.sort_values('ID')
    sorted_indices = df_sorted['ID'].searchsorted(tabulation_bin_id_masked)

    # Clip indices to valid range to avoid out-of-bounds access
    sorted_indices = np.clip(sorted_indices, 0, len(df_sorted) - 1)

    # Get the average values (float array, don't modify original tabulation_bin_id_masked)
    relative_frequency_arr = df_sorted[average_col].values[sorted_indices].astype(np.float32)

    # Calculate areal_resolution_of_map_pixels
    in_ds4 = gdal.Open(risk30)
    P1 = in_ds4.GetGeoTransform()[1]
    P2 = abs(in_ds4.GetGeoTransform()[5])
    areal_resolution_of_map_pixels = P1 * P2 / 10000

    # Relative_frequency multiplied by the areal resolution of the map pixels to express the probabilities as densities
    fit_density_arr=relative_frequency_arr * areal_resolution_of_map_pixels

    # Create the final fit_density_map image using tabulation_bin_image function
    if out_fn2:
        print(f"Saving density map: {os.path.basename(out_fn2)}")
        # ignore_cleanup_errors: a stray GDAL handle must not bury the real error.
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_folder:
            temp_out = os.path.join(temp_folder, "temp_fit_density.tif")
            array_to_image(risk30, temp_out, fit_density_arr, gdal.GDT_Float32, -1)

            # Apply mask: where risk30 has data, keep fit density values, otherwise set to nodata
            expression = "if(map1[1] != no_data, map2[1], no_data)"
            raster_calculator(
                input_files=[risk30, temp_out],
                output_file=out_fn2,
                expression=expression,
                out_dtype="float32"
            )
        print("=" * 60 + "\n")

    return fit_density_arr

# Calculate Adjustment Ratio (AR) in CNF
