# Frequency Table Implementation Changes: Verra UDef-ARP vs TerraCover

This document describes the modifications made to the frequency table calculation in TerraCover's VT7 implementation compared to the original Verra UDef-ARP code.

## Overview

The frequency table is a critical component of the VT0007 methodology that calculates the relative frequency of deforestation within each modeling region (combination of vulnerability class and administrative division). TerraCover's implementation includes several improvements to handle edge cases and ensure data integrity.

---

## 1. NoData Value Handling in Modeling Regions

### Original Verra Code

The original implementation does not explicitly handle NoData values from input rasters:

```python
# Verra: allocation_tool.py, lines 74-83
arr1 = self.image_to_array(risk30_hrp)
arr2 = self.image_to_array(municipality)

# Simple mask based only on risk30 > 0
mask_arr_HRP = np.where(arr1 > 0, 1, arr1)

# Calculate tabulation bin id with mask
tabulation_bin_id_masked = np.add(arr1*1000, arr2) * mask_arr_HRP
```

**Issue**: If either the vulnerability map or administrative divisions raster contains NoData values, these could be incorrectly included in calculations, leading to invalid modeling region IDs.

### TerraCover Implementation

The new implementation explicitly reads and excludes NoData values from both input rasters:

```python
# TerraCover: frequency_analysis.py, lines 56-88
ds1 = gdal.Open(risk30)
band1 = ds1.GetRasterBand(1)
nodata_risk30 = band1.GetNoDataValue()
arr1 = band1.ReadAsArray().astype(np.int64)

ds2 = gdal.Open(municipality)
band2 = ds2.GetRasterBand(1)
nodata_municipality = band2.GetNoDataValue()
arr2 = band2.ReadAsArray().astype(np.int64)

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

tabulation_bin_id_masked = (arr1 * 1000 + arr2) * mask_arr_HRP
```

**Improvement**: Ensures that only valid pixels from both input rasters contribute to the frequency table calculations.

---

## 2. Data Type for Modeling Region IDs

### Original Verra Code

Uses 16-bit signed integer, which limits the maximum ID value:

```python
# Verra: allocation_tool.py, lines 85-90
tabulation_bin_id_masked = tabulation_bin_id_masked.astype(np.int16)
self.array_to_image(risk30_hrp, out_fn1, tabulation_bin_id_masked, gdal.GDT_Int16, -1)
```

**Issue**: Int16 has a maximum value of 32,767. With the formula `vulnerability_class * 1000 + admin_division`, this limits:
- Maximum vulnerability class: 30 (standard VT0007)
- Maximum administrative division ID: ~2,767

If administrative division IDs exceed this range, integer overflow occurs.

### TerraCover Implementation

Uses 32-bit signed integer for safer range:

```python
# TerraCover: frequency_analysis.py, lines 91-97
# Use int64 arithmetic during calculation to prevent overflow
tabulation_bin_id_masked = (arr1 * 1000 + arr2) * mask_arr_HRP

# Convert to int32 for storage (range: -2 billion to +2 billion)
tabulation_bin_id_masked = tabulation_bin_id_masked.astype(np.int32)

# Use 0 as nodata value (IDs start from 1000, so 0 is safe)
array_to_image(risk30, out_fn1, tabulation_bin_id_masked, gdal.GDT_Int32, 0)
```

**Improvement**:
- Supports administrative division IDs up to ~2 million
- Uses 0 as NoData value (since valid IDs start at 1000)
- Performs intermediate calculations in int64 to prevent overflow

---

## 3. NoData Handling in Deforestation Raster

### Original Verra Code

Does not filter NoData values from the deforestation raster:

```python
# Verra: allocation_tool.py, lines 107-114
arr3 = self.image_to_array(deforestation_hrp)

# Direct multiplication without NoData filtering
deforestation_within_bin = tabulation_bin_id_masked * arr3
```

**Issue**: If the deforestation raster has NoData values (common at raster edges or outside study area), these could be incorrectly counted as valid deforestation pixels.

### TerraCover Implementation

Explicitly creates a valid mask excluding NoData and zero values:

```python
# TerraCover: frequency_analysis.py, lines 255-268
ds = gdal.Open(deforestation_hrp)
band = ds.GetRasterBand(1)
nodata_value = band.GetNoDataValue()
arr3 = band.ReadAsArray()

# Create mask to exclude nodata pixels
if nodata_value is not None:
    valid_mask = (arr3 != nodata_value) & (arr3 != 0)
else:
    valid_mask = (arr3 != 0)

# Apply mask: only process valid deforestation pixels (value = 1, excluding nodata)
deforestation_within_bin = np.where(valid_mask, tabulation_bin_id_masked * arr3, 0)
```

**Improvement**: Ensures accurate deforestation counts by excluding NoData pixels from the calculation.

---

## 4. Missing Bins Handling in Prediction Phase

This is the most significant change, addressing cases where modeling regions exist in the prediction phase but not in the fitting phase.

### Original Verra Code

Uses outer join but does not handle cases where entire vulnerability zones are absent:

```python
# Verra: allocation_tool.py, lines 514-561
def calculate_missing_bins_rf(self, id_difference, csv):
    df = pd.read_csv(csv)
    df['v_zone'] = (df['ID'] // 1000).astype(int)

    missing_v_zone = [x // 1000 for x in id_difference]

    # Select rows from same vulnerability zones
    filtered_df = df[df['v_zone'].isin(missing_v_zone)].copy()

    # ... calculate weighted averages ...

    # Outer join - leaves NaN if v_zone doesn't exist in fitting phase
    missing_bins_df = pd.merge(id_difference_df, aggregated_df, on='v_zone', how='outer')

    # NaN values are NOT handled - remain in the dataframe
    df_new = pd.concat([df, missing_bins_df], ignore_index=True)
```

**Issue**: When a vulnerability zone (e.g., v_zone=1) exists in the prediction phase but has no corresponding data in the fitting phase:
- The merge produces NaN values for Average Deforestation
- These NaN values propagate to the density map calculation
- Can cause errors or undefined behavior in subsequent processing

### TerraCover Implementation

Explicitly detects and handles missing vulnerability zones:

```python
# TerraCover: frequency_analysis.py, lines 108-230
def calculate_missing_bins_rf(fitting_frequency_df, prediction_modeling_regions_array,
                               fitting_frequency_table_path):
    # Get unique IDs from fitting and prediction phases
    fitting_ids = set(fitting_frequency_df['ID'].values)
    prediction_ids = set(np.unique(prediction_modeling_regions_array[...]))

    id_difference = prediction_ids - fitting_ids

    if len(id_difference) == 0:
        return fitting_frequency_df

    df = fitting_frequency_df.copy()
    df['v_zone'] = (df['ID'] // 1000).astype(int)

    missing_v_zone = [x // 1000 for x in id_difference]

    # Identify v_zones that exist in fitting phase
    fitting_v_zones = set(df['v_zone'].values)

    # Identify MISSING v_zones (v_zones in prediction but not in fitting)
    missing_v_zones_set = set(missing_v_zone) - fitting_v_zones

    if missing_v_zones_set:
        print(f"Warning: {len(missing_v_zones_set)} vulnerability zone(s) "
              f"have no data in fitting phase: {sorted(missing_v_zones_set)}")
        print("These zones will be assigned Average Deforestation = 0")

    # Use LEFT join (not outer) to get weighted averages where available
    missing_bins_df = pd.merge(id_difference_df, aggregated_df, on='v_zone', how='left')

    # Fill NaN values with 0 for v_zones absent from fitting phase
    nan_count = missing_bins_df['Average Deforestation(pixel)'].isna().sum()
    if nan_count > 0:
        missing_bins_df = missing_bins_df.fillna(0)
        print(f"Filled {nan_count} bins with 0 (v_zones absent from fitting phase)")
```

**Improvement**:
- Explicitly identifies vulnerability zones that are completely absent from the fitting phase
- Assigns `Average Deforestation = 0` to these zones (conservative assumption)
- Provides clear warning messages about which zones were affected
- Uses LEFT join instead of OUTER join for cleaner logic
- Creates backup of original frequency table before modification

**Rationale for assigning 0**:
- Zones absent from fitting phase had no historical deforestation
- Lower vulnerability zones (e.g., v_zone=1) represent areas farthest from forest edges
- Assigning 0 is conservative and consistent with lack of historical data
- The iterative AR adjustment compensates by scaling other zones appropriately

---

## 5. Output Format Changes

### Original Verra Code

Saves frequency table as plain CSV:

```python
# Verra: allocation_tool.py, line 133
merged_df.to_csv(csv_file_path, index=False)
```

### TerraCover Implementation

Saves as formatted Excel file with proper number formatting:

```python
# TerraCover: frequency_analysis.py, lines 294-327
excel_file_path = xlsx_name if xlsx_name.endswith('.xlsx') else xlsx_name.replace('.csv', '.xlsx')

with pd.ExcelWriter(excel_file_path, engine='openpyxl') as writer:
    merged_df.to_excel(writer, index=False, sheet_name='Relative Frequency')

    worksheet = writer.sheets['Relative Frequency']

    # Set column widths
    worksheet.column_dimensions['A'].width = 55 / 7
    worksheet.column_dimensions['B'].width = 170 / 7
    worksheet.column_dimensions['C'].width = 140 / 7
    worksheet.column_dimensions['D'].width = 190 / 7

    # Apply number formatting
    for row in range(2, len(merged_df) + 2):
        # Total Deforestation(pixel) - comma separator, no decimals
        cell_b = worksheet.cell(row=row, column=2)
        if isinstance(cell_b.value, (int, float)):
            cell_b.number_format = '#,##0'

        # Area of the Bin(pixel) - comma separator, no decimals
        cell_c = worksheet.cell(row=row, column=3)
        if isinstance(cell_c.value, (int, float)):
            cell_c.number_format = '#,##0'

        # Average Deforestation(pixel) - 5 decimals
        cell_d = worksheet.cell(row=row, column=4)
        if isinstance(cell_d.value, (int, float)):
            cell_d.number_format = '0.00000'
```

**Improvement**:
- Easier to read and review in Excel
- Proper number formatting (thousands separators, decimal places)
- Column widths optimized for content

---

## 6. Relative Frequency Map Generation

### Original Verra Code

Does not generate a relative frequency raster map.

### TerraCover Implementation

Optionally generates a raster map showing relative frequency values:

```python
# TerraCover: frequency_analysis.py, lines 329-357
if map_output_path is not None:
    print(f"Creating relative frequency map: {os.path.basename(map_output_path)}")

    # Create a copy to map IDs to relative frequency values
    relative_frequency_map = tabulation_bin_id_masked.copy().astype(np.float32)

    # Map IDs to Average Deforestation values
    df_sorted = merged_df_with_zero.sort_values('ID')
    sorted_indices = df_sorted['ID'].searchsorted(tabulation_bin_id_masked)
    relative_frequency_map[:] = df_sorted['Average Deforestation(pixel)'].values[sorted_indices]

    # Apply mask from deforestation raster
    expression = "if(map1[1] != no_data, map2[1], no_data)"
    raster_calculator(
        input_files=[deforestation_hrp, temp_out],
        output_file=map_output_path,
        expression=expression,
        out_dtype="float32"
    )
```

**Improvement**: Provides visual representation of relative frequency distribution across the study area.

---

## Summary of Changes

| Component | Verra Implementation | TerraCover Implementation |
|-----------|---------------------|---------------------------|
| NoData handling (inputs) | Not handled | Explicit exclusion |
| Data type for IDs | Int16 (max 32,767) | Int32 (max 2 billion) |
| NoData handling (deforestation) | Not handled | Explicit exclusion |
| Missing v_zones | NaN values remain | Assigned 0 with warning |
| Output format | CSV | Formatted Excel |
| Relative frequency map | Not generated | Optional output |
| Backup of original table | Created | Created with `_orig` suffix |

---

## Files Modified

- **Original Verra file**: `verra_code/UDef-ARP-main/allocation_tool.py`
- **TerraCover implementation**: `vt7/frequency_analysis.py`

---

## Status in UDef-ARP v2.11

**Verdict: NOT FIXED in v2.11** — all three issues persist unchanged from the Original.

| Sub-issue | v2.11 evidence (`allocation_tool.py`) | Status |
|-----------|----------------------------------------|--------|
| NoData in risk/vulnerability raster | line 80: `mask_arr_HRP = np.where(arr1 > 0, 1, arr1)` — still no `GetNoDataValue()` | NOT FIXED |
| NoData in deforestation raster | line 112: `...[deforestation_within_bin != 0]` — only a `!= 0` filter, no NoData check | NOT FIXED |
| Int16 overflow (region IDs) | lines 86 & 192: `.astype(np.int16)`; lines 90 & 194: `gdal.GDT_Int16` (fitting and prediction) | NOT FIXED |

v2.11 keeps the same `np.int16` storage (capping region IDs) and the same implicit NoData handling in both `tabulation_bin_id_HRP` and `tabulation_bin_id_VP`. Only TerraCover uses int64 for calculation / int32 for storage and explicit NoData filtering.

---

## Version History

| Date | Author | Changes |
|------|--------|---------|
| 2025 | TerraCover | Initial implementation with improvements |
