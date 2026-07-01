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
- Calculation of missing bins with relative frequency
- Creation of relative frequency tables
- Creation of fit density maps
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
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
    from terracover.modules.vt7.utils import array_to_image, raster_calculator


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
def calculate_missing_bins_rf(fitting_frequency_df, prediction_modeling_regions_array, fitting_frequency_table_path):
    '''
    If one or more empty bins are found in prediction phase, compute the jurisdiction-wide weighted average
    of relative frequencies for missing bins and update the frequency table.

    This is applied when modeling regions exist in the Prediction phase but not in the Fitting phase.

    When a vulnerability zone (v_zone) exists in the prediction phase but has no corresponding data
    in the fitting phase (i.e., the entire v_zone is absent from the fitting frequency table),
    the missing bins are assigned Average Deforestation = 0. This is appropriate because:
    - These zones had no historical deforestation (hence absent from fitting phase)
    - Lower vulnerability zones (e.g., v_zone=1) represent areas farthest from forest edges
    - Assigning 0 is conservative and consistent with the lack of historical deforestation data
    - The iterative AR adjustment will compensate by scaling other zones appropriately

    :param fitting_frequency_df: DataFrame with relative frequency table from fitting phase
    :param prediction_modeling_regions_array: Array of modeling region IDs from prediction phase
    :param fitting_frequency_table_path: Path to the fitting frequency table Excel file (will be backed up and updated)
    :return: Updated frequency table DataFrame with missing bins filled
    '''
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

    if missing_v_zones_set:
        print(f"  Warning: {len(missing_v_zones_set)} vulnerability zone(s) have no data in fitting phase: {sorted(missing_v_zones_set)}")
        print(f"  These zones will be assigned Average Deforestation = 0 (no historical deforestation)")

    # Select rows from the same vulnerability zones as missing bins
    filtered_df = df[df['v_zone'].isin(missing_v_zone)].copy()

    # Calculate total deforestation for weighted average
    filtered_df['Total Deforestation(pixel)'] = filtered_df['Area of the Bin(pixel)'] * filtered_df['Average Deforestation(pixel)']

    # Group by vulnerability zone and sum area and weighted relative frequency
    aggregated_df = filtered_df.groupby('v_zone')[['Total Deforestation(pixel)', 'Area of the Bin(pixel)']].sum().reset_index()

    # Calculate Average Deforestation for each vulnerability zone
    aggregated_df['Average Deforestation(pixel)'] = aggregated_df['Total Deforestation(pixel)'] / aggregated_df['Area of the Bin(pixel)']

    # Create dataframe for missing IDs
    id_difference_df = pd.DataFrame(id_difference, columns=['ID'])
    id_difference_df['v_zone'] = missing_v_zone

    # Create missing bins dataframe by merging with aggregated vulnerability zone data
    missing_bins_df = pd.merge(id_difference_df, aggregated_df, on='v_zone', how='left')

    # Fill NaN values with 0 for v_zones that don't exist in fitting phase
    # This handles the case where an entire vulnerability zone is absent from the fitting phase
    # (e.g., v_zone=1 appears in VP but never existed in HRP due to forest area reduction)
    nan_count = missing_bins_df['Average Deforestation(pixel)'].isna().sum()
    if nan_count > 0:
        missing_bins_df = missing_bins_df.fillna(0)
        print(f"  Filled {nan_count} bins with 0 (v_zones absent from fitting phase)")

    # Drop v_zone column from missing bins (keep only the needed columns)
    missing_bins_df = missing_bins_df[['ID', 'Total Deforestation(pixel)', 'Area of the Bin(pixel)', 'Average Deforestation(pixel)']]

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
            # Total Deforestation(pixel) - column 2
            cell_b = worksheet.cell(row=row, column=2)
            if isinstance(cell_b.value, (int, float)):
                cell_b.number_format = '#,##0'

            # Area of the Bin(pixel) - column 3
            cell_c = worksheet.cell(row=row, column=3)
            if isinstance(cell_c.value, (int, float)):
                cell_c.number_format = '#,##0'

            # Average Deforestation(pixel) - column 4
            cell_d = worksheet.cell(row=row, column=4)
            if isinstance(cell_d.value, (int, float)):
                cell_d.number_format = '0.00000'

    print(f"Frequency table updated with {len(id_difference)} missing bins.")

    return df_new

# Create Relative Frequency Table
def create_relative_frequency_table(tabulation_bin_id_masked, deforestation_hrp, xlsx_name, map_output_path=None):
    """
    Create relative frequency table and optionally a raster map
    :param tabulation_bin_id_masked: array with id and total deforestation
    :param deforestation_hrp: Deforestation Map during the CAL/HRP (path to raster file)
    :param xlsx_name: output Excel file path
    :param map_output_path: optional path for output relative frequency raster map (default: None, no map created)
    :return: merged_df: relative frequency dataframe
    """
    import tempfile

    print("=" * 60)
    print("Creating Relative Frequency Table")
    print("=" * 60)
    print(f"Analyzing deforestation within modeling regions...")

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
    df1 = pd.DataFrame(arr_counts_deforestion, columns=['ID', 'Total Deforestation(pixel)'])
    df2 = pd.DataFrame(arr_counts, columns=['ID', 'Area of the Bin(pixel)'])

    # Merge the two DataFrames based on the 'id' column using an outer join to include all rows from both DataFrames
    merged_df = pd.merge(df1, df2, on='ID', how='outer').fillna(0)

    # Calculate Average Deforestation by performing the division operation of col2 and col3 and add a new column to merged_df
    merged_df['Average Deforestation(pixel)'] = merged_df.iloc[:, 1].astype(float) / merged_df.iloc[:, 2].astype(float)

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

            # Total Deforestation(pixel) - column 2: comma separator, no decimals
            cell_b = worksheet.cell(row=row, column=2)
            if isinstance(cell_b.value, (int, float)):
                cell_b.number_format = '#,##0'

            # Area of the Bin(pixel) - column 3: comma separator, no decimals
            cell_c = worksheet.cell(row=row, column=3)
            if isinstance(cell_c.value, (int, float)):
                cell_c.number_format = '#,##0'

            # Average Deforestation(pixel) - column 4: 5 decimals
            cell_d = worksheet.cell(row=row, column=4)
            if isinstance(cell_d.value, (int, float)):
                cell_d.number_format = '0.00000'

    # Create relative frequency raster map if output path is provided
    if map_output_path is not None:
        print(f"Creating relative frequency map: {os.path.basename(map_output_path)}")
        # Create a copy of tabulation_bin_id_masked to map IDs to relative frequency values
        relative_frequency_map = tabulation_bin_id_masked.copy().astype(np.float32)

        # Insert index=0 row for background (ID=0)
        new_row = pd.DataFrame({'ID': [0], 'Total Deforestation(pixel)': [0],
                                'Area of the Bin(pixel)': [0], 'Average Deforestation(pixel)': [0]})
        merged_df_with_zero = pd.concat([new_row, merged_df]).reset_index(drop=True)

        # Using numpy.searchsorted() to map IDs to relative frequency values
        df_sorted = merged_df_with_zero.sort_values('ID')
        sorted_indices = df_sorted['ID'].searchsorted(tabulation_bin_id_masked)
        relative_frequency_map[:] = df_sorted['Average Deforestation(pixel)'].values[sorted_indices]

        # Save relative frequency map to temporary file, then apply mask
        with tempfile.TemporaryDirectory() as temp_folder:
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
def create_fit_density_map(risk30, tabulation_bin_id_masked, merged_df, out_fn2=None):
    '''
    Create the fitting density map, this function used for fitting phase (CAL and HRP)
    :param risk30: the 30-class vulnerability map for the CAL/HRP
    :param tabulation_bin_id_masked: array for tabulation bin id in fitting Phase
    :param merged_df: relative frequency dataframe
    :param out_fn2: optional output file path
    :return:
    '''
    import tempfile

    print("=" * 60)
    print("Creating Fitting/Prediction Density Map")
    print("=" * 60)

    # Insert index=0 row into first row of merged_df DataFrame
    new_row = pd.DataFrame({'ID': [0], 'Total Deforestation(pixel)': [0], 'Area of the Bin(pixel)': [0],
                            'Average Deforestation(pixel)': [0]})
    merged_df = pd.concat([new_row, merged_df]).reset_index(drop=True)

    # Using numpy.searchsorted() to assign values to 'id'
    df_sorted = merged_df.sort_values('ID')
    sorted_indices = df_sorted['ID'].searchsorted(tabulation_bin_id_masked)

    # Clip indices to valid range to avoid out-of-bounds access
    sorted_indices = np.clip(sorted_indices, 0, len(df_sorted) - 1)

    # Get the average deforestation values (float array, don't modify original tabulation_bin_id_masked)
    relative_frequency_arr = df_sorted['Average Deforestation(pixel)'].values[sorted_indices].astype(np.float32)

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
        with tempfile.TemporaryDirectory() as temp_folder:
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
