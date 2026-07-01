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

## Comparison with UDef-ARP v2.11

Verra released **UDef-ARP v2.11** (`UDef-ARP-main 2.11`) after the original reference code. This section evaluates whether v2.11 resolves the unidirectional AR bug described above.

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

---
