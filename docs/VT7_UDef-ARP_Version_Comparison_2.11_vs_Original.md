# UDef-ARP Code Comparison: Version 2.11 vs Original

## Comprehensive Analysis of Differences and Bug Resolution Status

**Document Version:** 1.0
**Date:** March 2026
**Author:** TerraCover Development Team

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Directory Structure Differences](#2-directory-structure-differences)
3. [UDef-ARP.py (Main GUI Application)](#3-udef-arpy-main-gui-application)
4. [allocation_tool.py](#4-allocation_toolpy)
5. [vulnerability_map.py](#5-vulnerability_mappy)
6. [model_evaluation.py](#6-model_evaluationpy)
7. [UI Files (.ui)](#7-ui-files-ui)
8. [README.md](#8-readmemd)
9. [Bug Resolution Analysis](#9-bug-resolution-analysis)
10. [Geometric Classification Formula Comparison](#10-geometric-classification-formula-comparison)
11. [Conclusions](#11-conclusions)
12. [AR Iteration: TerraCover vs v2.11 — Detailed Code Comparison](#12-ar-iteration-terracover-vs-v211--detailed-code-comparison)
13. [Geometric Classification: Three-Way Comparison (Original vs v2.11 vs TerraCover)](#13-geometric-classification-three-way-comparison-original-vs-v211-vs-terracover)

---

## 1. Executive Summary

This document provides a detailed comparison between two versions of the Verra UDef-ARP (Unplanned Deforestation Allocation and Risk Mapping Procedure) code:

- **UDef-ARP-main 2.11** (referred to as "v2.11"): A newer version with incremental improvements
- **UDef-ARP-main** (referred to as "Original"): The base version

The analysis covers all file-level differences, code changes, and critically evaluates whether version 2.11 resolves the bugs previously identified and documented by the TerraCover development team.

### Key Findings

- Version 2.11 introduces **meaningful improvements** in GUI path handling, error reporting, TIF file support, and code flexibility (loop-based classification instead of hardcoded assignments).
- However, version 2.11 **does not resolve the majority of critical bugs** identified in the TerraCover documentation, including the geometric classification off-by-one error, the unidirectional AR adjustment, the `fmask` variable reference bug, and the missing vulnerability zone NaN propagation.
- The AR iterative adjustment bug is **partially addressed** (accumulative iteration is fixed) but introduces a **new issue** by removing the annual rate conversion in the VP workflow.

---

## 2. Directory Structure Differences

Both directories contain the same file structure with one exception:

| File | v2.11 | Original |
|------|-------|----------|
| `data/stage.PNG` | Present | **Missing** |
| All other files | Present | Present |

The `stage.PNG` image is referenced in v2.11's README.md to illustrate the "Fitting and Prediction Phases and Chronology of the Testing and Application Stages" from the VT0007 report.

Files with **no differences**: `LICENSE`, `UDef-ARP_conda_env.yml`, `font/AvenirNextLTPro-DemiCn.otf`, all files in `doc/`, and all image files in `data/` (except `stage.PNG`).

---

## 3. UDef-ARP.py (Main GUI Application)

This file contains the most extensive changes (~1,488 lines of diff output), primarily focused on GUI improvements rather than algorithmic changes.

### 3.1 Additional Imports

**v2.11** adds:
```python
from PyQt5.QtWidgets import QPushButton, QTextEdit, QSizePolicy
import traceback
```

These support the enhanced error dialog introduced in v2.11.

### 3.2 File Path Handling

**v2.11** introduces `pathlib`-based path handling:

```python
# v2.11
self.in_fn = Path(PureWindowsPath(file_path))
self.file_path_directory = '\\'.join(file_path.split('/')[:-1])
```

```python
# Original
self.in_fn = file_path  # Raw string path
```

**v2.11** also introduces:
- **Directory tracking variables**: `self.file_path_directory`, `self.file_path2_directory`, etc., to remember the last-used directory for each file input.
- **Unique variable names** for file dialogs: Uses `file_path2`, `file_path3`, `file_path4`, `file_path5`, `file_path6` instead of reusing `file_path` for every dialog.
- **`get_full_path()` helper method**: Resolves relative paths against the working directory.

### 3.3 Enhanced Error Dialogs

**v2.11** replaces simple error messages with detailed, copyable error dialogs:

```python
# v2.11: Rich error dialog with traceback
error_box = QMessageBox(self)
error_box.setIcon(QMessageBox.Critical)
error_box.setWindowTitle("Error")
error_box.setText(f"<b>An Error Occurred During Processing</b>")
error_box.setDetailedText(tb)  # Full traceback

# Copy button for error message
copy_button = QPushButton("Copy Error Message")
error_box.addButton(copy_button, QMessageBox.ActionRole)
```

```python
# Original: Simple error message
QMessageBox.critical(self, "Error", f"An error occurred during processing: {str(e)}")
```

### 3.4 Mask Parameter for Benchmark Model

**v2.11** passes the mask to the geometric classification:

```python
# v2.11
mask_arr = self.vulnerability_map.geometric_classification(self.in_fn, NRT, n_classes, self.mask)

# Original
mask_arr = self.vulnerability_map.geometric_classification(self.in_fn, NRT, n_classes)
```

### 3.5 Input Validation Changes

**v2.11** validates inputs earlier in `process_data2_nrt()`, resolving paths against directories before checking for missing inputs. The original performs validation after path assignment.

### 3.6 RST and TIF Support in `rdc_correct`

This pattern appears across multiple files. **v2.11** adds support for `.tif` files when correcting reference system metadata in `.rdc` sidecar files:

```python
# v2.11: Handles both .rst and .tif files
if in_fn.split('.')[-1] == 'rst':
    # Read reference system from .rdc file
    with open(read_file_name + '.rdc', 'r') as read_file:
        for line in read_file:
            if line.startswith("ref. system :"):
                correct_name = line
                break
elif in_fn.split('.')[-1] == 'tif':
    # Read projection from .tif using GDAL
    dataset = gdal.Open(in_fn)
    projection = dataset.GetProjection()
    ref_system_name = projection.split('PROJCS["')[1].split('"')[0]
    # Write to .rdc file
    write_file.write(f"ref. system : {ref_system_name}\n")
```

```python
# Original: Only handles .rst files
read_file_name, _ = os.path.splitext(in_fn)
write_file_name, _ = os.path.splitext(out_fn)
with open(read_file_name + '.rdc', 'r') as read_file:
    for line in read_file:
        if line.startswith("ref. system :"):
            correct_name = line
            break
```

---

## 4. allocation_tool.py

### 4.1 New Method: `adjusted_prediction_density_map_annual`

The **Original** version contains a method not present in v2.11:

```python
# Original only
def adjusted_prediction_density_map_annual(self, prediction_density_arr, risk30_vp, AR, out_fn2, time):
    '''Create adjusted prediction density map for annual'''
    maximum_density = P1 * P2 / 10000
    adjusted_prediction_density_arr = AR * prediction_density_arr
    adjusted_prediction_density_arr[adjusted_prediction_density_arr > maximum_density] = maximum_density
    adjusted_prediction_density_arr_annual = adjusted_prediction_density_arr / time
    self.array_to_image(risk30_vp, out_fn2, adjusted_prediction_density_arr_annual, gdal.GDT_Float32, -1)
```

This method applies AR to the density array and then divides by time to produce an annual rate. Note that this applies AR **again** after the iterative loop, which constitutes a bug (see Section 9.2).

### 4.2 `execute_workflow_cal` Changes

| Aspect | v2.11 | Original |
|--------|-------|----------|
| Return value | `(id_difference, iteration_count)` | `id_difference` only |
| Loop accumulation | `prediction_density_arr = new_prediction_density_arr` (accumulative) | Does **not** reassign (non-accumulative) |
| Missing bins | `csv = self.calculate_missing_bins_rf(id_difference, csv, pre_model_region_id)` | `self.calculate_missing_bins_rf(id_difference, csv)` |

**v2.11** correctly reassigns the prediction density array inside the while loop:

```python
# v2.11: Accumulative iteration (correct per VT0007)
while AR > 1.00001 and iteration_count <= max_iterations:
    new_prediction_density_arr = self.adjusted_prediction_density_array(prediction_density_arr, ...)
    AR = self.calculate_adjustment_ratio_cnf(new_prediction_density_arr, ...)
    prediction_density_arr = new_prediction_density_arr  # <-- ACCUMULATIVE
    iteration_count += 1
```

```python
# Original: Non-accumulative (bug)
while AR > 1.00001 and iteration_count <= max_iterations:
    new_prediction_density_arr = self.adjusted_prediction_density_array(prediction_density_arr, ...)
    AR = self.calculate_adjustment_ratio_cnf(new_prediction_density_arr, ...)
    iteration_count += 1
    # prediction_density_arr never updated -- always uses original
```

### 4.3 `execute_workflow_vp` Changes

| Aspect | v2.11 | Original |
|--------|-------|----------|
| Function signature | No `time` parameter | Includes `time` parameter |
| Final output | `self.adjusted_prediction_density_map(...)` | `self.adjusted_prediction_density_map_annual(..., time)` |
| Return value | `(id_difference, iteration_count)` | `id_difference` only |
| Loop accumulation | Accumulative | Non-accumulative |

**Critical difference**: v2.11 calls `adjusted_prediction_density_map` (which applies AR again but does **not** divide by time), while the Original calls `adjusted_prediction_density_map_annual` (which applies AR again **and** divides by time to produce an annual rate).

This means **v2.11 removes the annual rate conversion entirely** in the VP workflow, which contradicts the VT0007 methodology requirement: *"As a final step, convert the result back to an annual rate by dividing by the number of years in the BVP."*

### 4.4 `check_modeling_region_ids` Changes

| Aspect | v2.11 | Original |
|--------|-------|----------|
| Return value | `(id_difference, pre_model_region_id)` | `id_difference` only |

**v2.11** returns an additional array `pre_model_region_id` containing the unique modeling region IDs from the prediction phase. This is used to filter the frequency table in `calculate_missing_bins_rf`.

### 4.5 `calculate_missing_bins_rf` Changes

| Aspect | v2.11 | Original |
|--------|-------|----------|
| Parameters | `(id_difference, csv, pre_model_region_id)` | `(id_difference, csv)` |
| Filtering | Merges with `pre_model_region_id` to filter by prediction region | No filtering |
| Output file | Creates `_adjusted_for_prediction` CSV | Overwrites original CSV (with `_orig` backup) |
| Return value | Returns new CSV path | No return value |

**v2.11** filters the frequency table to include only modeling regions that exist in the prediction phase:

```python
# v2.11
mr_cnf_df = pd.DataFrame(pre_model_region_id, columns=['ID'])
df_new_cnf = pd.merge(df_new, mr_cnf_df, on='ID', how='inner')
new_csv = f"{base}_adjusted_for_prediction{ext}"
df_new_cnf.to_csv(new_csv, index=False)
return new_csv
```

```python
# Original
shutil.copyfile(csv, csv.split('.')[0] + '_orig' + '.csv')
df_new.to_csv(csv, index=False)
```

### 4.6 `rdc_correct` Changes

Same TIF/RST dual support pattern as described in Section 3.6.

---

## 5. vulnerability_map.py

### 5.1 `bin_width` Data Type

```python
# v2.11
bin_width = P

# Original
bin_width = int(P)
```

**v2.11** keeps the bin width as a float, while the Original casts to integer. This affects the precision of bin calculations.

### 5.2 `geometric_classification` (Benchmark Model)

| Aspect | v2.11 | Original |
|--------|-------|----------|
| Signature | `(self, in_fn, NRT, n_classes, mask)` | `(self, in_fn, NRT, n_classes)` |
| Mask handling | Multiplies array by external mask | Uses array directly |
| Boundary clamping | Sets `risk_class[n_classes-1][1] = LL` and `risk_class[0][0] = NRT` | No explicit clamping |
| Classification | Loop-based (`for i in range(n_classes)`) | Hardcoded 29 individual lines |
| Progress reporting | Inside loop (`if i % 5 == 0`) | Separate `emit()` calls per 5 classes |

**v2.11** adds a `mask` parameter and multiplies the distance array by it before classification:

```python
# v2.11
mask_arr0 = self.image_to_array(mask)
mask_arr = arr * mask_arr0
mask_arr[mask_arr >= NRT] = 1
```

```python
# Original
mask_arr = arr
mask_arr[arr >= NRT] = 1
```

**v2.11** uses a compact loop for classification:

```python
# v2.11
for i in range(n_classes):
    lower = risk_class[i][0]
    upper = risk_class[i][1]
    mask_arr[(lower > mask_arr) & (mask_arr >= upper)] = i + 2
```

```python
# Original: 29 hardcoded lines
mask_arr[(risk_class[0][0] > mask_arr) & (mask_arr >= risk_class[0][1])] = 2
mask_arr[(risk_class[1][0] > mask_arr) & (mask_arr >= risk_class[1][1])] = 3
# ... 27 more lines ...
mask_arr[(risk_class[28][0] > mask_arr) & (mask_arr >= risk_class[28][1])] = 30
```

### 5.3 `geometric_classification_alternative` (Alternative Model)

This is where the **formula itself differs** between versions:

| Aspect | v2.11 | Original |
|--------|-------|----------|
| Ratio formula | `r = (UL/LL)^(1/n_classes)` | `r = (LL/UL)^(1/n_classes)` |
| Risk class formula | `risk_class = LL + (UL - LL * r^class_array)` | `risk_class = UL * r^class_array` |
| Boundary clamping | `risk_class[0][1] = LL` | No clamping |
| max_value handling | Calculates `max_value` if metadata absent | No fallback |
| Classification | Loop-based | Hardcoded 30 lines |

These two formulas produce fundamentally different class boundary distributions (see Section 10 for detailed mathematical comparison).

### 5.4 `FlushCache` Calls

The **Original** includes explicit cache flushing after raster writes:

```python
# Original only
out_band.FlushCache()
out_ds.FlushCache()
```

**v2.11** omits these calls, which could potentially cause data loss if the program terminates before the operating system flushes write buffers.

### 5.5 `rdc_correct` Changes

Same TIF/RST dual support pattern as described in Section 3.6.

---

## 6. model_evaluation.py

### 6.1 Mask Polygon Creation

| Aspect | v2.11 | Original |
|--------|-------|----------|
| Layer name | `POLYGONIZED_MASK` (single step) | `TEMP_POLYGONIZED` then `POLYGONIZED_MASK` (two steps) |
| Polygon selection | Keeps **all** polygons directly | Selects **largest polygon only** |

**v2.11** keeps all polygons from the mask in a single step:

```python
# v2.11
temp_layername = "POLYGONIZED_MASK"
temp_ds = driver.CreateDataSource(temp_layername + ".shp")
temp_layer = temp_ds.CreateLayer(temp_layername, srs=spatial_ref)
gdal.Polygonize(in_band, in_band, temp_layer, -1, [], callback=None)
# All polygons retained
```

The **Original** first creates all polygons, then extracts only the largest one into a separate shapefile:

```python
# Original
temp_layername = "TEMP_POLYGONIZED"
# ... create all polygons ...
features = [(feature.GetGeometryRef().GetArea(), feature) for feature in temp_layer]
largest_polygon = max(features, key=lambda item: item[0])[1]
# Create final shapefile with only the largest polygon
final_layername = "POLYGONIZED_MASK"
# ... write only largest_polygon ...
```

### 6.2 Thiessen Polygon Generation

| Aspect | v2.11 | Original |
|--------|-------|----------|
| Mask for Voronoi generation | Uses `mask_df` directly | Uses `unary_union` of `mask_df` geometry |
| Edge filtering mask | `mask_df` | `polydf` (GeoDataFrame from `unary_union`) |

```python
# v2.11
thiessen_gdf = self.remove_edge_cells(voronois, mask_df, 0.999)

# Original
polygon = mask_df.geometry.unary_union
polydf = gpd.GeoDataFrame(geometry=[polygon], crs=mask_df.crs)
thiessen_gdf = self.remove_edge_cells(voronois, polydf, 0.999)
```

The Original creates a `unary_union` of the mask geometry and converts it to a GeoDataFrame before passing to edge filtering. The v2.11 passes the mask GeoDataFrame directly.

### 6.3 Scatter Plot Changes

| Aspect | v2.11 | Original |
|--------|-------|----------|
| Data type | `np.float32` | `np.float64` |
| Extended X range | `X_extended = np.linspace(0, xmax, 500)` | Uses actual X values |
| Trend line | Plotted over `X_extended` | Plotted over `X` |
| 1:1 line | Plotted over `X_extended` | Plotted as `[0, max(X)]` to `[0, max(X)]` |
| Theil-Sen regression | **Included** | **Not included** |
| Scatter alpha | `alpha=0.5` | `edgecolors='white'` |
| OLS label | `'OLS Line'` | `'Best Fit Line'` |
| Statistics shown | Theil-Sen eq., OLS eq., Samples, R^2, MedAE | Equation, Samples, R^2, MedAE |
| Axis limits | Set before plotting statistics | Set after plotting statistics |

**v2.11** adds Theil-Sen regression:

```python
# v2.11 only
ts_slope, ts_intercept, _, _ = stats.theilslopes(Y, X)
y_pred = ts_slope * X_extended + ts_intercept
ts_equation = f'Y = {ts_slope:.4f} * X + {ts_intercept:.2f}'
plt.plot(X_extended, y_pred, color='orange', linestyle='-', label='Theil-Sen Line')
```

### 6.4 `rdc_correct` Changes

Same TIF/RST dual support pattern as described in Section 3.6.

---

## 7. UI Files (.ui)

All `.ui` files (except `intro_screen.ui`) contain minor differences:

| Aspect | v2.11 | Original |
|--------|-------|----------|
| Font weight | `<weight>8</weight>` (ExtraBold) | `<weight>7</weight>` (Bold) |

Additionally, some label texts were changed:

| v2.11 | Original |
|-------|----------|
| `Administrative Divisions image` | `Map of Administrative Divisions` |
| `Vulnerability image for the CAL (previous step)` | `Vulnerability Map for the CAL (previous step)` |
| `Deforestation in the CAL` | `Map of Deforestation in the CAL (binary map)` |

The Original label texts are more descriptive (e.g., specifying "binary map" for deforestation, and "Map of" prefix for clarity).

---

## 8. README.md

| Aspect | v2.11 | Original |
|--------|-------|----------|
| Stage diagram | Embedded `stage.PNG` image with caption | No image |
| VT0007 link | Hyperlinked to Verra PDF | Plain text |
| Windows installer | Mentioned as option #2 | Not mentioned |
| Notes numbering | 4 items (1-4) | 3 items (1-3) |
| Projection emphasis | **Bold**: "All map data are required to be on an **Equal Area Projection**" | Plain: "All map data are required to be on an equal area projection" |
| Format description | Same | Same |

---

## 9. Bug Resolution Analysis

This section evaluates whether version 2.11 resolves each bug documented in the TerraCover `vt7/docs/` folder.

### 9.1 Geometric Classification Off-by-One Error

**Document:** `VT7_Geometric_Distribution_Analysis.md`
**Status:** NOT RESOLVED

The bug: when `n_classes=30`, the code creates 30 geometric intervals plus 1 implicit class for "beyond NRT", resulting in 31 total classes instead of the user-specified 30.

Both v2.11 and the Original use `n_classes` directly in the ratio formula instead of `n_classes - 1`:

```python
# Both versions (benchmark model)
r = np.power(LL / UL, 1 / n_classes)  # Should be 1 / (n_classes - 1)
```

TerraCover's fix uses `n_classes - 1`:

```python
# TerraCover corrected
n_classes_within_nrt = n_classes - 1
r = np.power(LL / UL, 1 / n_classes_within_nrt)
```

Additionally, the Original still uses hardcoded 29-line assignments (inflexible), while v2.11 improves this to a loop. However, the fundamental off-by-one error persists in both.

### 9.2 AR Iterative Adjustment Bug (Non-Accumulative + Extra AR Application)

**Document:** `VT7_Adjustment_Ratio_Implementation_Analysis.md`
**Status:** PARTIALLY RESOLVED

**Bug #1 (Non-accumulative iteration):** FIXED in v2.11.

v2.11 adds `prediction_density_arr = new_prediction_density_arr` inside the while loop, making the iteration accumulative as specified by VT0007.

**Bug #2 (Extra AR application when saving):** NOT FIXED.

Both versions call a function that applies AR to the array again when saving the output. In v2.11, this is `adjusted_prediction_density_map`; in the Original, it is `adjusted_prediction_density_map_annual`. Since the loop already produces a converged array (AR approximately equal to 1.0), applying AR again is mathematically redundant but technically incorrect.

**New Issue Introduced by v2.11:** The VP workflow no longer converts the output to an annual rate, as the `time` parameter was removed from `execute_workflow_vp`. The VT0007 methodology explicitly requires: *"convert the result back to an annual rate by dividing by the number of years in the BVP."*

### 9.3 Variable Reference Bug (`fmask` vs `arr_fmask`)

**Document:** `VT7_Deforestation_Map_Variable_Reference_Bug.md`
**Status:** NOT RESOLVED

The bug at line 487 of `model_evaluation.py` compares a file path string (`fmask`) against the integer 1 instead of comparing the NumPy array (`arr_fmask`). This causes the "Forest at start of HRP" category (value 1) to never be assigned in the combined deforestation map.

Neither version corrects this bug. The comparison `(fmask == 1)` always evaluates to `False` because a string can never equal an integer.

### 9.4 Missing Vulnerability Zones (NaN Propagation)

**Document:** `VT7_Missing_Vulnerability_Zones_Bug_Fix.md`
**Status:** NOT RESOLVED

When an entire vulnerability zone exists in the prediction phase but is absent from the fitting phase, the frequency table merge produces NaN values that propagate to the density map and AR calculation.

Neither version handles this case. v2.11 adds filtering by `pre_model_region_id`, which changes the behavior of the frequency table but does not address the NaN propagation issue. TerraCover's fix assigns `Average Deforestation = 0` for missing zones with explicit warnings.

### 9.5 Unidirectional AR Adjustment (AR > 1 Only)

**Document:** `VT7_AR_Adjustment_Bug_Fixes.md`
**Status:** NOT RESOLVED

Both versions use the condition `while AR > 1.00001`, which only adjusts when the model underestimates deforestation. When the model overestimates (AR < 1), the loop never executes and the density map retains inflated values.

TerraCover's fix uses bidirectional convergence:

```python
# TerraCover corrected
inverse_tolerance = 1.0 / tolerance
while (AR > tolerance or AR < inverse_tolerance) and iteration_count < max_iterations:
```

### 9.6 Frequency Table Issues (NoData, Int16 Overflow)

**Document:** `VT7_Frequency_table_changes.md`
**Status:** NOT RESOLVED

Neither version addresses:
- **NoData handling**: Both versions do not explicitly exclude NoData values from input rasters
- **Int16 overflow**: Both versions use `np.int16` for modeling region IDs, limiting administrative division IDs to ~2,767
- **Deforestation NoData**: Both versions do not filter NoData values from the deforestation raster

TerraCover uses `int64` for calculations, `int32` for storage, and explicit NoData filtering.

### 9.7 Dual-Mask System for Thiessen Polygons

**Document:** `VT7_Evaluation_Improvements.md`
**Status:** NOT RESOLVED

Both versions use a single mask for Voronoi generation and edge filtering. The Original selects the largest polygon only, while v2.11 keeps all polygons. However, neither implements the dual-mask approach (separate masks for grid generation vs. statistics with exclusions).

The approach difference between v2.11 and Original actually represents a **regression** in v2.11: by keeping all polygons from the mask (which may include small fragments), the Voronoi generation may be affected by noisy geometry. The Original at least ensures a clean, single polygon boundary by selecting the largest.

> **Note (context matters):** "keeping all polygons" is a regression only **in the absence of** the dual-mask system. The same change is an *improvement* inside TerraCover's dual-mask pipeline (grid generated against the full continuous jurisdiction, exclusions applied only after edge filtering, fragments dissolved back to their Voronoi-cell IDs), because there the retained fragments never reach grid generation. v2.11 adopted the "keep all polygons" building block without that surrounding machinery, so it inherits the downside with none of the upside. See `VT7_Evaluation_Improvements.md` → "Reconciling an apparent contradiction between the TerraCover documents" for the full reconciliation.

### 9.8 Summary Table

| Bug | Document | v2.11 | Original | TerraCover |
|-----|----------|-------|----------|------------|
| Geometric off-by-one | `VT7_Geometric_Distribution_Analysis.md` | Not fixed | Not fixed | Fixed |
| AR non-accumulative iteration | `VT7_Adjustment_Ratio_Implementation_Analysis.md` | **Fixed** | Not fixed | Fixed |
| AR extra application when saving | `VT7_Adjustment_Ratio_Implementation_Analysis.md` | Not fixed | Not fixed | Fixed |
| Annual rate conversion in VP | `VT7_Adjustment_Ratio_Implementation_Analysis.md` | **Removed** (new issue) | Present | Fixed |
| `fmask` vs `arr_fmask` | `VT7_Deforestation_Map_Variable_Reference_Bug.md` | Not fixed | Not fixed | Fixed |
| Missing v_zones NaN | `VT7_Missing_Vulnerability_Zones_Bug_Fix.md` | Not fixed | Not fixed | Fixed |
| AR unidirectional (> 1 only) | `VT7_AR_Adjustment_Bug_Fixes.md` | Not fixed | Not fixed | Fixed |
| NoData handling | `VT7_Frequency_table_changes.md` | Not fixed | Not fixed | Fixed |
| Int16 overflow | `VT7_Frequency_table_changes.md` | Not fixed | Not fixed | Fixed |
| Dual-mask Thiessen | `VT7_Evaluation_Improvements.md` | Not fixed | Not fixed | Fixed |

**Score: v2.11 resolves 1 of 10 identified issues, partially addresses 1, and introduces 1 new issue.**

---

## 10. Geometric Classification Formula Comparison

The alternative model (`geometric_classification_alternative`) uses fundamentally different formulas between the two versions. This section provides a detailed mathematical comparison with a worked example.

### 10.1 Formula Definitions

**Parameters for both versions:**
- `UL` = Upper Limit (2.0 for rescaled ETP)
- `LL` = Lower Limit (1.0 for rescaled ETP)
- `n_classes` = Number of classes (e.g., 5)
- `class_array` = Array of `[i, i+1]` pairs, reversed from `n-1` down to `0`

**Original formula:**
```
r = (LL / UL)^(1/n_classes)
risk_class = UL * r^(class_array)
```

**v2.11 formula:**
```
r = (UL / LL)^(1/n_classes)
risk_class = LL + (UL - LL * r^(class_array))
```

### 10.2 Mathematical Relationship

The ratios are inverses of each other:

```
r_original = (LL/UL)^(1/n)
r_v2.11    = (UL/LL)^(1/n) = 1 / r_original
```

The risk class formulas are NOT mathematically equivalent:

```
Original:  boundary = UL * (LL/UL)^(i/n) = UL^(1 - i/n) * LL^(i/n)
v2.11:     boundary = LL + UL - LL * (UL/LL)^(i/n) = LL + UL - UL^(i/n) * LL^(1 - i/n)
```

### 10.3 Worked Example

**Parameters:** UL = 2, LL = 1, n_classes = 5

**Original:**
```
r = (1/2)^(1/5) = 0.8706
```

| Class | class_array | Upper = UL*r^i | Lower = UL*r^(i+1) | Width |
|-------|------------|----------------|---------------------|-------|
| 1 (low risk) | [4, 5] | 2 * 0.8706^4 = 1.1487 | 2 * 0.8706^5 = 1.0000 | 0.1487 |
| 2 | [3, 4] | 2 * 0.8706^3 = 1.3195 | 2 * 0.8706^4 = 1.1487 | 0.1709 |
| 3 | [2, 3] | 2 * 0.8706^2 = 1.5157 | 2 * 0.8706^3 = 1.3195 | 0.1963 |
| 4 | [1, 2] | 2 * 0.8706^1 = 1.7411 | 2 * 0.8706^2 = 1.5157 | 0.2254 |
| 5 (high risk) | [0, 1] | 2 * 0.8706^0 = 2.0000 | 2 * 0.8706^1 = 1.7411 | 0.2589 |

**Total width: 1.0002** (covers [1.0, 2.0])

**v2.11:**
```
r = (2/1)^(1/5) = 1.1487
```

| Class | class_array | Upper = 3 - r^i | Lower = 3 - r^(i+1) | Width |
|-------|------------|------------------|----------------------|-------|
| 1 (low risk) | [4, 5] | 3 - 1.1487^4 = 1.2589 | 3 - 1.1487^5 = 1.0000* | 0.2589 |
| 2 | [3, 4] | 3 - 1.1487^3 = 1.4843 | 3 - 1.1487^4 = 1.2589 | 0.2254 |
| 3 | [2, 3] | 3 - 1.1487^2 = 1.6805 | 3 - 1.1487^3 = 1.4843 | 0.1963 |
| 4 | [1, 2] | 3 - 1.1487^1 = 1.8513 | 3 - 1.1487^2 = 1.6805 | 0.1709 |
| 5 (high risk) | [0, 1] | 3 - 1.1487^0 = 2.0000 | 3 - 1.1487^1 = 1.8513 | 0.1487 |

*Explicitly clamped to LL = 1.0

**Total width: 1.0002** (covers [1.0, 2.0])

### 10.4 Visual Comparison

```
ETP Range (rescaled):  1.0 ──────────────────────────────────── 2.0

ORIGINAL (class widths increase toward high ETP/risk):
Class: │  1    │   2     │    3      │     4       │      5        │
       1.00  1.15     1.32       1.52         1.74            2.00
       ◄ low risk                                   high risk ►
       (narrow)                                     (wide)

v2.11 (class widths decrease toward high ETP/risk):
Class: │      1        │     2       │    3      │   4     │  5    │
       1.00           1.26         1.48       1.68     1.85   2.00
       ◄ low risk                                   high risk ►
       (wide)                                       (narrow)
```

### 10.5 Practical Implications

| Aspect | Original | v2.11 |
|--------|----------|-------|
| High-risk class width | Wide (0.2589) | Narrow (0.1487) |
| Low-risk class width | Narrow (0.1487) | Wide (0.2589) |
| Pixel distribution (high risk) | More pixels per class | Fewer pixels per class |
| Pixel distribution (low risk) | Fewer pixels per class | More pixels per class |
| Sensitivity | Higher sensitivity to low-risk variations | Higher sensitivity to high-risk variations |

**Interpretation:**

The **Original** formula creates wider classes at the high-risk end of the spectrum. This means more pixels are grouped together in high-risk classes, potentially losing discrimination between areas with different levels of high vulnerability.

The **v2.11** formula reverses this: narrow classes at the high-risk end provide finer discrimination where it matters most (areas most likely to be deforested), while low-risk areas (unlikely to be deforested) are grouped into broader classes.

From a methodological standpoint, the v2.11 approach is arguably better for deforestation risk mapping because it provides more granularity where deforestation is most likely to occur.

### 10.6 Comparison with TerraCover's Corrected Implementation

TerraCover uses a **normalized** approach that guarantees complete, gap-free coverage:

```python
# TerraCover: Normalized deltas
raw_deltas = r ** np.arange(n_classes)
deltas = (UL - LL) * raw_deltas / raw_deltas.sum()
edges = LL + np.cumsum(np.insert(deltas, 0, 0))
risk_class = np.column_stack((edges[1:], edges[:-1]))
```

This approach ensures that the sum of all class widths exactly equals `(UL - LL)`, with no gaps or overlaps regardless of floating-point precision issues.

---

## 11. Conclusions

### 11.1 What v2.11 Improves

1. **GUI usability**: Better file path handling with `pathlib`, directory tracking, and unique variable names for file dialogs
2. **Error reporting**: Detailed error dialogs with tracebacks and copy functionality
3. **Code flexibility**: Loop-based classification instead of hardcoded 29-line assignments
4. **TIF support**: Dual RST/TIF handling in `rdc_correct` across all modules
5. **Accumulative AR iteration**: Fixes the non-accumulative loop bug in the AR adjustment process
6. **Mask parameter**: Benchmark model now accepts an external mask for classification
7. **Frequency table filtering**: Filters frequency table by prediction region IDs
8. **Theil-Sen regression**: Adds robust regression line to evaluation scatter plots
9. **Alternative model formula**: Changes class boundary distribution to favor high-risk discrimination

### 11.2 What v2.11 Does NOT Fix

1. **Geometric off-by-one error**: Still produces n+1 classes instead of n
2. **`fmask` variable reference bug**: Still compares string path to integer
3. **AR unidirectional**: Still only adjusts when AR > 1
4. **Missing vulnerability zone NaN**: Still allows NaN propagation
5. **NoData handling**: Still does not filter NoData from inputs
6. **Int16 overflow**: Still uses Int16 for modeling region IDs
7. **Dual-mask Thiessen**: Still uses single mask for evaluation
8. **Extra AR application**: Still applies AR when saving output

### 11.3 New Issues Introduced by v2.11

1. **Annual rate conversion removed**: The VP workflow no longer divides by VP years, contradicting VT0007 methodology
2. **Missing FlushCache**: Raster write operations no longer explicitly flush cache
3. **Float bin_width**: Removing the `int()` cast on bin_width may introduce floating-point precision issues in downstream calculations

### 11.4 Overall Assessment

Version 2.11 represents an incremental improvement focused primarily on **GUI enhancements and code maintainability** rather than algorithmic correctness. Of the 10 critical bugs documented by the TerraCover team, only 1 is fully resolved, 1 is partially resolved, and 1 new issue is introduced. The TerraCover implementation remains the only version that comprehensively addresses all identified bugs and implements the VT0007 methodology as specified.

---

## 12. AR Iteration: TerraCover vs v2.11 — Detailed Code Comparison

This section compares the **Adjustment Ratio (AR) iteration** between the TerraCover implementation (`terracover/modules/vt7/adjustment.py`) and v2.11 (`verra_code/UDef-ARP-main 2.11/allocation_tool.py`), and evaluates whether the two produce the same results.

### 12.1 What Is Identical

The **core iterative loop is mathematically the same** — both are now accumulative:

```python
# v2.11 (execute_workflow_cnf, line 428)      # TerraCover (iterative_ar_adjustment, line 176)
while AR > 1.00001 ...:                         while (AR > tol or AR < inv_tol) ...:
    new = AR * pred (clamp to max)                 current = AR * current (clamp to max)
    AR  = recompute(new)                            AR = recompute(current)
    pred = new   # accumulative                     # current already reassigned — accumulative
```

The recurrence `pred_k = AR_{k-1} · pred_{k-1}` (with clamping to `maximum_density`) is identical, iteration by iteration.

### 12.2 Differences That Change the Result

| # | Aspect | v2.11 | TerraCover | Affects result? |
|---|--------|-------|------------|-----------------|
| 1 | **Direction** | `while AR > 1.00001` — only corrects when the model **underestimates** | `while AR > tol or AR < 1/tol` — **bidirectional** | **Yes**, when AR < 1 (overestimation) |
| 2 | **Extra multiplication when saving** | `adjusted_prediction_density_map()` re-applies `AR_final * array` (line 435/318) | Saves the converged array **directly**, no extra multiply (line 214/227) | **Yes** |
| 3 | **NoData in AD** | `arr5 * resolution` sums **all** pixels, including NoData (line 251) | Masks `(arr5 == 1) & (arr5 != nodata)` (line 77) | **Yes**, when the map contains NoData |
| 4 | **Annual rate (VP)** | Removed — does not divide by years | `vp_years` divides to an annual rate (line 209) | **Yes**, in the VP phase |
| 5 | **Iteration bound** | `iteration_count <= max` → up to max+1 | `iteration_count < max` → exactly max | Marginal |
| 6 | **Output masking** | `array_to_image` with nodata −1 | `raster_calculator` masks to the valid area of risk30 | Format / NoData |

### 12.3 Would the Results Be the Same?

**No, not in general.** It depends on the scenario:

**Ideal case** — clean deforestation map (only 0/1, no NoData), AR > 1, and convergence before the maximum number of iterations:
- The intermediate arrays match exactly.
- But when **saving**, v2.11 applies `AR_final × converged_array` one extra time (difference #2). Since `AR_final ≤ 1.00001`, the result is **almost identical** (differs by ≤ ~0.001% plus a re-applied clamp). In practice, effectively the same.

**Real cases where they diverge materially:**
- **Overestimation (AR < 1):** in v2.11 the loop *never runs*; it saves `AR_initial × raw_density` (a single, non-converged adjustment). TerraCover iterates bidirectionally until convergence. → **Different results.**
- **Map with NoData** (e.g. 255 in uint8): v2.11 inflates AD by summing NoData → wrong AR → the entire adjusted density is off. TerraCover excludes it. → **Very different.**
- **Non-convergence** (reaches the maximum with AR still > 1): v2.11's extra multiplication applies an additional partial adjustment that TerraCover does not. → **Different.**
- **VP phase:** v2.11 does not convert to an annual rate; TerraCover does (when `vp_years` is provided). → **Different scale.**

**Summary:** the *iteration algorithm* is the same (both accumulative), but because of (2) the extra multiplication when saving, (1) the unidirectional condition, and (3) the NoData handling in AD, **the results coincide only approximately in the clean, convergent, AR > 1 case; in any other scenario they differ, sometimes significantly.**

---

## 13. Geometric Classification: Three-Way Comparison (Original vs v2.11 vs TerraCover)

Section 10 compared the *alternative* model between the Original and v2.11. This section extends the analysis to all three implementations — Original (`verra_code/UDef-ARP-main`), v2.11 (`verra_code/UDef-ARP-main 2.11`), and TerraCover (`terracover/modules/vt7/geometric_classification.py`) — for **both** the benchmark and alternative models, and resolves an apparent paradox: v2.11 and TerraCover use *reciprocal* geometric ratios yet produce **identical** class boundaries.

### 13.1 Benchmark Model (`geometric_classification`)

All three use `LL` = pixel spatial resolution and `UL` = NRT. Differences:

| Aspect | Original | v2.11 | TerraCover |
|--------|----------|-------|------------|
| Ratio `r` | `(LL/UL)^(1/n)` | `(LL/UL)^(1/n)` | **`(LL/UL)^(1/(n−1))`** |
| Geometric intervals | n | n | **n−1** |
| Class assignment | 29 **hardcoded** lines (2–30) | **loop**, classes 2..**31** | **loop**, classes 2..30 (high→low) |
| Boundary clamp | none | `risk_class[n−1][1]=LL`, `[0][0]=NRT` | implicit (n−1 lands exactly on LL) |
| Mask | none | `arr * mask` in place | via `raster_calculator` at the end |
| Compares against | `mask_arr` (mutated in place) | `mask_arr` (mutated in place) | **`arr` (immutable copy)** |
| **Total classes (n=30)** | 30 **but with a gap** | **31 (off-by-one)** | **30 exactly** |
| Arbitrary `n` support | **n=30 only** (hardcoded) | any n | any n |

**The off-by-one, concretely (n=30):** all three build `risk_class[i] = UL·r^[i, i+1]` with `r<1`, where `risk_class[0]` sits near NRT (low risk) and the last near LL (high risk, forest edge):

- **Original** — `r = (LL/UL)^(1/30)` → 30 intervals, but only `risk_class[0..28]` are assigned (classes 2–30). The interval `risk_class[29] = [UL·r²⁹, LL]` is **never assigned**: the highest-risk sliver `[LL, UL·r²⁹)` keeps raw distance values. → 30 classes *with a gap at the most important edge*. Being hardcoded to 29 lines, it **only works for n=30**.
- **v2.11** — same `r = ^(1/30)` → 30 intervals; the loop assigns `risk_class[0..29]` → classes 2..**31**, and the clamp closes the edge. Covers everything but **produces 31 classes** instead of the requested 30.
- **TerraCover** — `n_classes_within_nrt = n−1 = 29`, `r = (LL/UL)^(1/29)` → 29 intervals covering `[LL, UL]` exactly → classes 2–30, plus class 1 (≥NRT). **Exactly 30 classes, no gap, no overflow.** The last interval ends exactly at LL by construction (`UL·r²⁹ = LL`), so no clamp is needed.

In the benchmark model the **distribution shape is the same in all three** (wide classes far from the edge / low risk, narrow near the edge / high risk). The only mathematical difference is the exponent denominator (`n` vs `n−1`) and how the last band is covered.

### 13.2 Alternative Model (`geometric_classification_alternative`) — Formulas

Input is an empirical vulnerability map `[0,1]` rescaled to `[1,2]` (`LL=1`, `UL=2`); high risk = value near 2.

| Aspect | Original | v2.11 | TerraCover |
|--------|----------|-------|------------|
| Ratio `r` | `(LL/UL)^(1/n) = (½)^(1/n)` | **`(UL/LL)^(1/n) = 2^(1/n)`** (inverse) | `(LL/UL)^(1/n) = (½)^(1/n)` |
| Boundary formula | `UL·r^k` | `LL+(UL−LL·r^k) = 3 − r^k` | normalized cumulative deltas |
| Width distribution | **wide at HIGH risk** | wide at LOW risk (fine at high) | wide at LOW risk (fine at high) |
| Coverage sum | geometric partition | reflected geometric | **exactly `UL−LL`, gap-free** |
| `max_value` | `GetMaximum()`, no fallback | `GetMaximum()` + `np.max` fallback | **`np.max` of valid data, excludes NoData** |
| Clamp | none | `risk_class[0][1]=LL` | not needed (normalized) |
| Classes | 1..30 hardcoded | 1..n loop | 1..n loop |

TerraCover's normalized formulation:

```python
raw_deltas = r ** np.arange(n_classes)            # [1, r, r², …]  (decreasing)
deltas     = (UL - LL) * raw_deltas / raw_deltas.sum()   # normalized: Σ = UL−LL
edges      = LL + np.cumsum(np.insert(deltas, 0, 0))
risk_class = np.column_stack((edges[1:], edges[:-1]))
```

### 13.3 Why v2.11 and TerraCover Produce Identical Boundaries Despite Reciprocal `r`

At first glance v2.11 (`r₂ = 2^(1/n)`, >1) and TerraCover (`r_T = (½)^(1/n) = 1/r₂`, <1) look opposite. They are not: the reciprocal ratio is **exactly compensated** by v2.11's reflected boundary formula (`3 − r^k`) and TerraCover's cumulative construction. Comparing the actual class edges:

**v2.11** boundaries, for `k = 0…n`:

```
edge_k = 3 − r₂^k = 3 − 2^(k/n)
```

**TerraCover** boundaries — expanding the normalized cumulative sum:

```
edge_m = LL + (UL−LL) · (1 − r_T^m)/(1 − r_T^n)
       = 1 + (1 − r_T^m)/(1 − ½)
       = 3 − 2·r_T^m
       = 3 − 2^((n−m)/n)
```

As `m` runs `0…n`, the exponent `(n−m)/n` sweeps the same values `k/n` as v2.11. **Both yield the identical edge set** (just enumerated in reverse):

```
{ 3 − 2^(k/n) : k = 0…n }
```

Therefore they classify identically. Numerically, the class widths also sum to exactly 1 in **both** (not 1.0002 — that figure in Section 10.3 is 4-decimal rounding of the illustrative table): `Σ widths_v2.11 = r₂^n − 1 = 2 − 1 = 1`.

**Worked edges (n=5, UL=2, LL=1):** both v2.11 and TerraCover give `{1, 1.2589, 1.4843, 1.6805, 1.8513, 2}`.

By contrast, the **Original** uses `UL·r^k = 2^(k/n)`, giving the *mirror-image* edge set `{2^(k/n)} = {1, 1.1487, 1.3195, 1.5157, 1.7411, 2}` — reflected about the midpoint 1.5, which is why the Original has wide classes at the **high-risk** end (coarser discrimination where deforestation is most likely).

### 13.4 Where v2.11 and TerraCover Alternative Results *Can* Still Differ

The boundaries are identical, so any divergence comes from the **input being classified** and numerical robustness, not the formula:

1. **`max_value` in the `[1,2]` rescaling** (`arr_rescale = 1 + arr/max_value`): v2.11 reads `GetMaximum()` metadata (falling back to `np.max` only if absent); TerraCover **always** recomputes `np.max` over valid pixels, **excluding NoData**. With stale metadata or NoData present, v2.11 rescales differently → classifies different values → **different results**. With correct metadata and no NoData → identical.
2. **Floating-point coverage**: v2.11 computes each edge as `3 − r^k` directly; TerraCover's normalized cumsum **guarantees** `Σ = (UL−LL)` with no drift or gaps. Negligible in the clean case, but TerraCover is immune to rounding-induced gaps.

**Conclusion:** the reciprocal `r` is purely cosmetic — v2.11 and TerraCover implement the **same** alternative-model boundaries. TerraCover's advantages are robustness (guaranteed gap-free coverage, NoData-aware rescaling), not a different class distribution. The **Original** alternative model, however, is genuinely different (mirror-image distribution). For the **benchmark** model, TerraCover is the only version with the correct class count (`n−1` interior intervals → exactly `n` total).

---

## References

1. VT0007 Tool: Unplanned Deforestation Allocation and Risk Mapping Procedure (Verra)
2. TerraCover Bug Documentation: `terracover/modules/vt7/docs/`
3. Original UDef-ARP Code: `verra_code/UDef-ARP-main/`
4. UDef-ARP v2.11 Code: `verra_code/UDef-ARP-main 2.11/`
5. TerraCover Implementation: `terracover/modules/vt7/`

---

*Document Version: 1.0*
*Date: March 2026*
*Author: TerraCover Development Team*
