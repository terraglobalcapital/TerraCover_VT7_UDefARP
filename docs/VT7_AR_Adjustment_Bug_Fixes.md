# VT7 Bug Fixes: AR Bidirectional Adjustment and ETP Metadata Classification

## Overview

Two bugs were identified and fixed that caused the VT7 UDEF-ARP module to produce incorrect density maps and allocation results. Both bugs originate from the Verra UDef-ARP reference implementation.

---

## Bug 1: AR Iterative Adjustment Only Applied When AR > 1

### Issue Summary

The iterative Adjustment Ratio (AR) convergence loop only executed when AR > 1 (model underestimates deforestation). When AR < 1 (model overestimates deforestation), zero iterations were performed and the density map retained inflated values.

### Bug Location

- **File**: `terracover/modules/vt7/adjustment.py`
- **Function**: `iterative_ar_adjustment`
- **Line**: 175
- **Also present in**: Original Verra UDef-ARP code (`allocation_tool.py` lines 438, 484; `BVP_density_mapping.py` line 409; `train_multi_logit_for_TerraChange.py` line 409)

### Root Cause

The while loop condition only checked one direction:

```python
while AR > tolerance and iteration_count < max_iterations:
```

Where `tolerance = 1.00001`. This means:
- **AR = 1.15** (underestimation): Loop executes, adjusts density upward, converges toward 1.0
- **AR = 0.88** (overestimation): Loop **never executes**, density map is not adjusted

### Impact

In real-world scenarios where the model overestimates deforestation (common when using ETP-based alternative models), the density map values were ~10-15% higher than expected. For example:

| Metric | Expected | Actual (before fix) |
|--------|----------|---------------------|
| JNR AD (expected deforestation) | 141,731 ha | 141,731 ha |
| JNR MD (modeled deforestation) | Should converge to AD | 160,621 ha |
| AR | Should converge to ~1.0 | 0.882 (no iterations) |
| Density sum (ha/year) | 23,622 | 26,770 (+13.3%) |

### Fix Applied

Changed the loop condition to handle both directions:

```python
# Before (broken):
while AR > tolerance and iteration_count < max_iterations:

# After (fixed):
inverse_tolerance = 1.0 / tolerance
while (AR > tolerance or AR < inverse_tolerance) and iteration_count < max_iterations:
```

The convergence check in the log was also updated:

```python
# Before:
log_lines.append(f"  Converged: {'Yes' if AR <= tolerance else 'No (max iterations reached)'}")

# After:
converged = inverse_tolerance <= AR <= tolerance
log_lines.append(f"  Converged: {'Yes' if converged else 'No (max iterations reached)'}")
```

With `tolerance = 1.00001`, convergence now requires `0.99999 <= AR <= 1.00001`.

### Files Modified

- `terracover/modules/vt7/adjustment.py`
- `terracover/modules/vt7/standalone/vt7_udef_arp/terracover/modules/vt7/adjustment.py`

---

## Bug 2: ETP-Based Vulnerability Rescaling Uses Stale Raster Metadata

### Issue Summary

In the alternative (ETP-based) vulnerability model, the empirical vulnerability map (value range `[0.0, 1.0]`) is rescaled to the `[1.0, 2.0]` range before geometric classification. The rescaling divides by `max_value`, which the original Verra code reads from the raster's GDAL **metadata** (`GetMaximum()`). When that metadata is stale, inherited from a parent raster, or absent, the rescaling factor is wrong and **every pixel is misclassified** into the wrong vulnerability class.

### Bug Location

- **File**: `terracover/modules/vt7/geometric_classification.py`
- **Function**: `geometric_classification_alternative`
- **Also present in**: Original Verra UDef-ARP code (`vulnerability_map.py`, `geometric_classification_alternative`)

### Root Cause

The rescaling step is:

```python
arr_rescale = 1 + arr * 1 / max_value
```

The original obtains `max_value` from raster metadata rather than from the data itself:

```python
# Verra original
max_value = in_band.GetMaximum()   # reads cached metadata, NOT the actual pixel data
arr_rescale = 1 + arr * 1 / max_value
```

`GetMaximum()` returns the statistic stored in the raster metadata, which can be:

- **Stale** — left over from a previous processing step whose value range differed.
- **Inherited** — copied from a parent/source raster during a GDAL operation.
- **Absent** — returns `None`, causing a `TypeError` in the division.

Because the `[1, 2]` rescaling is the input to the geometric classification, any error in `max_value` propagates to **all** class boundaries and therefore to every classified pixel.

### Impact

- If `max_value` is **larger** than the true data maximum, the rescaled values compress into the low end of `[1, 2]` → most pixels collapse into the lowest-risk classes.
- If `max_value` is **smaller** than the true maximum, rescaled values exceed 2.0 → pixels fall outside the highest class boundary and are left unclassified or clamped.
- If `max_value` is **`None`**, processing aborts with a `TypeError`.

In every case the alternative vulnerability map no longer reflects the true ETP distribution, invalidating the downstream density and allocation results.

### Fix Applied

TerraCover always computes `max_value` from the **actual pixel data**, excluding NoData:

```python
# Always compute max from actual data to avoid stale/inherited GDAL metadata
nodata = in_band.GetNoDataValue()
if nodata is not None:
    valid_mask = arr != nodata
    max_value = float(np.max(arr[valid_mask])) if np.any(valid_mask) else float(np.max(arr))
else:
    max_value = float(np.max(arr))

arr_rescale = 1 + arr * 1 / max_value
```

This guarantees the rescaling reflects the real value range of the input, is never `None`, and never counts NoData pixels toward the maximum.

### Files Modified

- `terracover/modules/vt7/geometric_classification.py`
- `terracover/modules/vt7/standalone/vt7_udef_arp/terracover/modules/vt7/geometric_classification.py`

---

## Comparison with UDef-ARP v2.11

Verra released **UDef-ARP v2.11** (`UDef-ARP-main 2.11`) after the original reference code. This section evaluates whether v2.11 resolves the two bugs described above.

### v2.11 does NOT fix the unidirectional AR bug

Both workflow functions in v2.11 keep the same one-directional loop condition as the Original:

```python
# UDef-ARP-main 2.11/allocation_tool.py
# execute_workflow_cnf (line 428) and execute_workflow_vp (line 475):
while AR > 1.00001 and iteration_count <= max_iterations:
```

When `AR < 1` (the model **overestimates** deforestation), the loop still **never executes**, and the density map keeps its inflated values — exactly the failure documented above. **This specific bug is not addressed in v2.11.** Only the TerraCover bidirectional condition (`while (AR > tolerance or AR < inverse_tolerance)`) handles overestimation.

### What v2.11 *did* change (separate, related sub-bugs)

v2.11 modified the same iteration loop for other reasons, which is worth noting to avoid confusion:

- **Accumulative iteration — FIXED.** v2.11 added `prediction_density_arr = new_prediction_density_arr` inside the loop, so each iteration builds on the previous result. The Original never reassigned the array (it always re-adjusted the initial density). TerraCover also applies AR accumulatively. *(See `VT7_Adjustment_Ratio_Implementation_Analysis.md`.)*
- **Extra AR application when saving — NOT fixed.** After the loop, v2.11 calls `adjusted_prediction_density_map()`, which multiplies the converged array by `AR` once more. TerraCover saves the converged array directly.
- **Annual-rate conversion in the VP workflow — REMOVED (regression).** v2.11 dropped the `time` parameter from `execute_workflow_vp`, so the Validity Period output is no longer divided by the number of years, contradicting the VT0007 requirement. TerraCover retains this via the `vp_years` parameter.

### Three-Way Summary

| Behavior | Original | v2.11 | TerraCover |
|----------|----------|-------|------------|
| AR loop direction | `AR > 1` only | `AR > 1` only | **bidirectional** |
| Handles overestimation (AR < 1) | No | **No** | **Yes** |
| Accumulative iteration | No | **Yes** | Yes |
| Extra AR multiply when saving | Yes | Yes | **No** |
| VP annual-rate conversion | Present | **Removed** | Present |
| NoData excluded from AD | No | No | **Yes** |

**Bottom line for the bidirectional AR bug:** neither Verra version fixes it — v2.11 behaves identically to the Original in the overestimation case. Only TerraCover converges the density map when `AR < 1`. A full cross-document evaluation of v2.11 is available in `VT7_UDef-ARP_Version_Comparison_2.11_vs_Original.md` (Sections 9.2 and 12).

### Bug 2 (ETP metadata rescaling): status in v2.11

v2.11 **partially** addresses Bug 2. It adds a fallback to `np.max` when the metadata is missing, but it still **prefers the metadata** (`GetMaximum()`) when present and does **not** exclude NoData:

```python
# UDef-ARP-main 2.11/vulnerability_map.py, geometric_classification_alternative:
max_value = in_band.GetMaximum()
if max_value is None:
    max_value = np.max(arr)
```

| Behavior | Original | v2.11 | TerraCover |
|----------|----------|-------|------------|
| Source of `max_value` | metadata (`GetMaximum()`) | metadata first, `np.max` fallback | **always `np.max` of data** |
| Handles absent metadata (`None`) | No (crashes) | **Yes** | Yes |
| Immune to stale/inherited metadata | No | **No** (still trusts it when present) | **Yes** |
| Excludes NoData from the maximum | No | No | **Yes** |

**Bottom line for Bug 2:** v2.11 fixes only the `None`/crash case. It still trusts stale or inherited metadata when it is present, and its `np.max` fallback does not exclude NoData — so the misclassification described above can still occur. Only TerraCover is fully immune. See also `VT7_Geometric_Distribution_Analysis.md` (Section 8.2) and `VT7_UDef-ARP_Version_Comparison_2.11_vs_Original.md` (Sections 5.3, 13.4).

---
