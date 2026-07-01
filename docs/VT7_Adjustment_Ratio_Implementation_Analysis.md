# VT7 Adjustment Ratio Implementation Analysis

## TerraCover vs. UDef-ARP (Verra Original): Critical Bug Fix in Iterative AR Process

---

## Executive Summary

This document provides a comprehensive technical analysis of the **Adjustment Ratio (AR) iterative process** as specified in the VT0007 methodology, comparing the original UDef-ARP (Verra) implementation against TerraCover's corrected implementation.

**Key Finding:** The original UDef-ARP code contains a **critical implementation bug** in the iterative AR adjustment loop that contradicts the VT0007 methodology specification. TerraCover corrects this bug and implements the methodology as specified.

---

## Table of Contents

1. [VT0007 Methodology Specification](#1-vt0007-methodology-specification)
2. [Implementation Comparison](#2-implementation-comparison)
3. [The Bug: Detailed Analysis](#3-the-bug-detailed-analysis)
4. [Mathematical Proof](#4-mathematical-proof)
5. [Code Comparison](#5-code-comparison)
6. [Impact Analysis](#6-impact-analysis)
7. [TerraCover Enhancements](#7-terracover-enhancements)
8. [Conclusion](#8-conclusion)

---

## 1. VT0007 Methodology Specification

### Official Methodology Text

The VT0007 methodology specifies the following process for quantity adjustment:

> **"To make the adjustment, use the following process:**
>
> **a)** Determine the expected deforestation (ED) for the period being modeled. In the testing stage, determine the total deforestation (in hectares) during the confirmation period. In the application stage, use the amount of deforestation (in hectares) as determined from the activity data estimation. Where the activity data amount is specified as an annual rate, multiply by the duration of the BVP to derive the total expected activity over the BVP. Converting the rate to total expected deforestation ensures that the adjustment does not allocate more deforestation to any pixel than is possible given its areal resolution. The final step in the adjustment process converts the result back to a per annum rate.
>
> **b)** Sum the pixels in the prediction density map. This is the modeled deforestation (MD).
>
> **c)** Calculate an adjustment ratio, AR, using the following formula: **AR = ED / MD** (Equation 3)
>
> **d)** Apply the adjustment ratio by multiplying AR by the prediction density map: **Adjusted_Prediction_Density_Map = AR × Prediction_Density_Map** (Equation 4)
>
> **e)** Check whether any pixels in the adjusted map exceed their maximum density. The maximum density is equal to the areal resolution of map pixels (e.g., 0.09 ha for 30 m data). It is very unlikely that the maximum density will be exceeded. However, if the density of deforestation exceeds the maximum for any pixels in the adjusted map, reclassify all pixels greater than the maximum (e.g., >0.09) to be the maximum, and **repeat stages b) and c) above**. Then, **when AR ≤ 1.00001** (six significant figures), **treat this as the final adjusted prediction density map**. Otherwise, **treat the result as the new prediction density map** and **repeat stages d) through e)** as many times as necessary to obtain AR ≤ 1.00001.
>
> **f)** As a final step, convert the result back to an annual rate by dividing by the number of years in the BVP."

### Key Interpretation Points

The critical phrase is: **"treat the result as the new prediction density map and repeat stages d) through e)"**

This explicitly states that:
1. The **result** of the current iteration becomes the input for the next iteration
2. The process is **accumulative** - each iteration builds upon the previous result
3. AR is applied to the **current adjusted array**, not the original array

---

## 2. Implementation Comparison

### Summary Table

| Aspect | VT0007 Methodology | TerraCover | UDef-ARP (Verra) |
|--------|-------------------|------------|------------------|
| Iteration base | Result of previous iteration | ✅ Correct | ❌ Uses original array |
| AR application | Accumulative | ✅ Correct | ❌ Non-accumulative |
| Final AR application | None (array already adjusted) | ✅ Correct | ❌ Applies AR again when saving |
| Convergence behavior | Guaranteed with iterations | ✅ Correct | ⚠️ Unpredictable |
| Annual conversion | Divide final result by years | ✅ Correct | ✅ Correct |

### Process Flow Diagrams

**VT0007 Methodology (Correct Flow):**

```
┌─────────────────────────────────────────────────────────────────┐
│                    INITIAL STATE                                 │
│  P₀ = Original Prediction Density Array                        │
│  MD₀ = Σ(P₀)                                                    │
│  AR₀ = ED / MD₀                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │      AR₀ > 1.00001 ?          │
              └───────────────────────────────┘
                    │                │
                   YES              NO
                    │                │
                    ▼                ▼
┌─────────────────────────────────┐  ┌─────────────────────────┐
│  ITERATION 1:                   │  │  OUTPUT:                │
│  P₁ = AR₀ × P₀                  │  │  P₀ / vp_years          │
│  P₁ = min(P₁, max_density)      │  │  (Already converged)    │
│  MD₁ = Σ(P₁)                    │  └─────────────────────────┘
│  AR₁ = ED / MD₁                 │
└─────────────────────────────────┘
                    │
                    ▼
              ┌───────────────────────────────┐
              │      AR₁ > 1.00001 ?          │
              └───────────────────────────────┘
                    │                │
                   YES              NO
                    │                │
                    ▼                ▼
┌─────────────────────────────────┐  ┌─────────────────────────┐
│  ITERATION 2:                   │  │  OUTPUT:                │
│  P₂ = AR₁ × P₁  ← ACCUMULATIVE  │  │  P₁ / vp_years          │
│  P₂ = min(P₂, max_density)      │  │  (Converged at iter 1)  │
│  MD₂ = Σ(P₂)                    │  └─────────────────────────┘
│  AR₂ = ED / MD₂                 │
└─────────────────────────────────┘
                    │
                    ▼
                  (...)
```

**UDef-ARP (Verra) - Incorrect Flow:**

```
┌─────────────────────────────────────────────────────────────────┐
│                    INITIAL STATE                                 │
│  P₀ = Original Prediction Density Array                        │
│  AR₀ = ED / Σ(P₀)                                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │      AR₀ > 1.00001 ?          │
              └───────────────────────────────┘
                    │                │
                   YES              NO
                    │                │
                    ▼                ▼
┌─────────────────────────────────┐  ┌─────────────────────────┐
│  ITERATION 1:                   │  │  (see below)            │
│  P₁ = AR₀ × P₀  ← FROM ORIGINAL │  └─────────────────────────┘
│  P₁ = min(P₁, max_density)      │
│  AR₁ = ED / Σ(P₁)               │
└─────────────────────────────────┘
                    │
                    ▼
              ┌───────────────────────────────┐
              │      AR₁ > 1.00001 ?          │
              └───────────────────────────────┘
                    │                │
                   YES              NO
                    │                │
                    ▼                ▼
┌─────────────────────────────────┐  ┌─────────────────────────────────┐
│  ITERATION 2:                   │  │  OUTPUT (BUG):                  │
│  P₂ = AR₁ × P₀  ← STILL ORIGINAL│  │  adjusted_prediction_map_annual │
│  (NOT P₁ as methodology states) │  │  (AR × P₁, max_cap) / time      │
│  P₂ = min(P₂, max_density)      │  │                                 │
│  AR₂ = ED / Σ(P₂)               │  │  ← APPLIES AR AGAIN!            │
└─────────────────────────────────┘  └─────────────────────────────────┘
```

---

## 3. The Bug: Detailed Analysis

### Bug #1: Non-Accumulative Iteration

**Location:** `allocation_tool.py`, lines 437-441 (CNF) and 484-487 (VP)

**UDef-ARP Code:**
```python
while AR > 1.00001 and iteration_count <= max_iterations:
    new_prediction_density_arr = self.adjusted_prediction_density_array(
        prediction_density_arr,  # ← BUG: Always uses ORIGINAL array
        risk30_vp,
        AR
    )
    AR = self.calculate_adjustment_ratio_cnf(new_prediction_density_arr, deforestation_cnf)
    iteration_count += 1
```

**Problem:** The variable `prediction_density_arr` (the original array) is used in every iteration instead of `new_prediction_density_arr` (the result of the previous iteration).

**Correct Implementation (TerraCover):**
```python
while AR > tolerance and iteration_count < max_iterations:
    current_density_arr = adjusted_prediction_density_array(
        current_density_arr,  # ← CORRECT: Uses result from previous iteration
        risk30,
        AR
    )
    AR, AD, MD = calculate_adjustment_ratio_cnf(current_density_arr, ...)
    iteration_count += 1
```

### Bug #2: Extra AR Application When Saving

**Location:** `allocation_tool.py`, lines 443-444 (CNF) and 490-491 (VP)

**UDef-ARP Code:**
```python
selected_density_arr = new_prediction_density_arr if new_prediction_density_arr is not None else prediction_density_arr
self.adjusted_prediction_density_map_annual(selected_density_arr, risk30_vp, AR, out_fn2, time)
```

The `adjusted_prediction_density_map_annual` function (lines 328-357):
```python
def adjusted_prediction_density_map_annual(self, prediction_density_arr, risk30_vp, AR, out_fn2, time):
    # ...
    # Adjusted_Prediction_Density_Map = AR x Prediction_Density_Map
    adjusted_prediction_density_arr = AR * prediction_density_arr  # ← APPLIES AR AGAIN!

    # Reclassify all pixels greater than the maximum
    adjusted_prediction_density_arr[adjusted_prediction_density_arr > maximum_density] = maximum_density

    # Convert to annual rate
    adjusted_prediction_density_arr_annual = adjusted_prediction_density_arr / time
```

**Problem:** This function multiplies the array by AR again before saving. When the loop exits with AR ≤ 1.00001, the array has already been adjusted. Applying AR again is mathematically incorrect.

**Methodology States:** "when AR ≤ 1.00001, treat this as the final adjusted prediction density map" - meaning no further AR application is needed.

**Correct Implementation (TerraCover):**
```python
# When loop exits, current_density_arr is already the final adjusted array
# Only divide by vp_years for annual conversion - NO additional AR application
output_density_arr = current_density_arr / vp_years
```

---

## 4. Mathematical Proof

### Scenario Setup

Consider a simple example:
- **P₀** (Original Prediction Density Array): Sum = 100 ha
- **ED** (Expected Deforestation): 150 ha
- **max_density**: 0.09 ha/pixel
- Assume 10 pixels exceed maximum after first adjustment

### Correct Process (VT0007 / TerraCover)

```
INITIAL:
  MD₀ = 100 ha
  AR₀ = 150 / 100 = 1.5

ITERATION 1:
  P₁ = 1.5 × P₀
  After capping: MD₁ = 145 ha (5 ha lost to cap)
  AR₁ = 150 / 145 = 1.0345

ITERATION 2:
  P₂ = 1.0345 × P₁  ← Accumulative
  After capping: MD₂ = 149.5 ha
  AR₂ = 150 / 149.5 = 1.0033

ITERATION 3:
  P₃ = 1.0033 × P₂  ← Accumulative
  After capping: MD₃ ≈ 150 ha
  AR₃ ≈ 1.0000 ✓ CONVERGED

OUTPUT: P₃ / vp_years
```

The process converges because each iteration brings MD closer to ED by adjusting the accumulated result.

### Incorrect Process (UDef-ARP)

```
INITIAL:
  MD₀ = 100 ha
  AR₀ = 150 / 100 = 1.5

ITERATION 1:
  P₁ = 1.5 × P₀  ← From original
  After capping: MD₁ = 145 ha
  AR₁ = 150 / 145 = 1.0345

ITERATION 2:
  P₂ = 1.0345 × P₀  ← BUG: From ORIGINAL, not P₁!
  After capping: MD₂ = 103.45 ha  ← REGRESSES!
  AR₂ = 150 / 103.45 = 1.45

ITERATION 3:
  P₃ = 1.45 × P₀  ← Still from original
  After capping: MD₃ = 144 ha
  AR₃ = 150 / 144 = 1.04

  ... OSCILLATES, does not converge properly ...

WHEN SAVING (with AR = 1.04):
  Output = (1.04 × P_selected) / time  ← Extra AR application!
```

The UDef-ARP process oscillates around the target because it always starts from the original array instead of building upon previous iterations.

### Why UDef-ARP "Works" Despite the Bug

The extra AR application when saving partially compensates for the non-accumulative bug:

1. The loop produces an array that is under-adjusted (because it always starts from original)
2. Applying AR again when saving adds the "missing" adjustment
3. However, this compensation is **not mathematically equivalent** to the correct accumulative process

The difference becomes significant when:
- Many pixels hit the maximum density cap
- Multiple iterations are needed
- The initial AR is significantly greater than 1

---

## 5. Code Comparison

### Function: Iterative AR Adjustment

#### UDef-ARP (allocation_tool.py)

```python
def execute_workflow_vp(self, directory, max_iterations, csv, municipality,
                        expected_deforestation, risk30_vp, out_fn1, out_fn2, time):
    '''
    Create workflow function for VP
    :param max_iterations: maximum number of iterations
    '''
    # ... setup code ...

    prediction_density_arr = self.calculate_prediction_density_arr(
        risk30_vp, tabulation_bin_id_VP_masked, csv
    )

    AR = self.calculate_adjustment_ratio(prediction_density_arr, expected_deforestation)

    iteration_count = 0
    new_prediction_density_arr = None

    # BUG: Always uses prediction_density_arr (original), not new_prediction_density_arr
    while AR > 1.00001 and iteration_count <= max_iterations:
        new_prediction_density_arr = self.adjusted_prediction_density_array(
            prediction_density_arr,  # ← ORIGINAL array used every time
            risk30_vp,
            AR
        )
        AR = self.calculate_adjustment_ratio(new_prediction_density_arr, expected_deforestation)
        iteration_count += 1

    if iteration_count <= int(max_iterations):
        selected_density_arr = new_prediction_density_arr if new_prediction_density_arr is not None else prediction_density_arr
        # BUG: Applies AR again in this function
        self.adjusted_prediction_density_map_annual(
            selected_density_arr, risk30_vp, AR, out_fn2, time
        )
    else:
        print("Maximum number of iterations reached.")
```

#### TerraCover (adjustment.py)

```python
def iterative_ar_adjustment(prediction_density_arr, risk30, out_fn, log_fn,
                            deforestation_cnf=None, max_iterations=5,
                            tolerance=1.00001, expected_deforestation=None,
                            vp_years=None):
    '''
    Iteratively adjust the prediction density array until AR converges to 1.0
    Following VT7 methodology: applies AR accumulatively to previous iteration's result
    '''
    # Start with the original prediction density array
    current_density_arr = prediction_density_arr.copy()

    # Calculate initial AR with components
    AR, AD, MD = calculate_adjustment_ratio_cnf(
        current_density_arr, deforestation_cnf,
        return_components=True,
        expected_deforestation=expected_deforestation
    )

    # Initialize logging
    log_lines = []
    log_lines.append(f"Initial State: MD={MD:.2f} ha, AD={AD:.2f} ha, AR={AR:.6f}")

    iteration_count = 0
    while AR > tolerance and iteration_count < max_iterations:
        iteration_count += 1

        # Apply AR to CURRENT array (accumulative per VT7 methodology)
        # VT7: "treat the result as the new prediction density map and repeat stages d)"
        current_density_arr = adjusted_prediction_density_array(
            current_density_arr,  # ← CORRECT: Uses result from previous iteration
            risk30,
            AR
        )

        # Recalculate AR based on the adjusted array
        AR, AD, MD = calculate_adjustment_ratio_cnf(
            current_density_arr, deforestation_cnf,
            return_components=True,
            expected_deforestation=expected_deforestation
        )

        log_lines.append(f"Iteration {iteration_count}: MD={MD:.2f} ha, AR={AR:.6f}")

    # Validate vp_years
    if vp_years is None or vp_years <= 0:
        raise ValueError(f"vp_years must be a positive integer > 0, got: {vp_years}")

    # Convert to annual rate - NO additional AR application
    output_density_arr = current_density_arr / vp_years

    # Write output and log
    # ...
```

### Key Differences Summary

| Aspect | UDef-ARP | TerraCover |
|--------|----------|------------|
| Loop variable | `prediction_density_arr` (original) | `current_density_arr` (updated each iteration) |
| AR in save function | Applied again | Not applied (already in array) |
| Logging | None | Detailed iteration-by-iteration logging |
| Validation | Minimal | Comprehensive (vp_years > 0, etc.) |
| Loop condition | `<=` max_iterations | `<` max_iterations |

---

## 6. Impact Analysis

### When Results Differ Most

The bug impact is most significant when:

1. **AR >> 1**: Large adjustments are needed
2. **Many pixels at cap**: Maximum density capping removes significant area
3. **Multiple iterations needed**: Bug compounds with each iteration

### Potential Consequences

| Scenario | UDef-ARP Result | TerraCover Result | Impact |
|----------|-----------------|-------------------|--------|
| AR ≈ 1.0 | Similar | Similar | Minimal difference |
| AR = 1.5, no caps | Similar (after extra AR) | Correct | Minor numerical difference |
| AR = 1.5, many caps | Over-adjusted | Correct | Significant difference |
| AR = 2.0+, many caps | Incorrect convergence | Correct | Major difference |

### Data Integrity Implications

Using the UDef-ARP implementation may result in:

1. **Incorrect deforestation predictions**: The Adjusted Prediction Density Map may not accurately represent expected deforestation
2. **Inconsistent model validation**: Testing stage comparisons may be based on incorrectly adjusted predictions
3. **Flawed carbon accounting**: If used for baseline calculations, carbon credits could be over- or under-estimated

---

## 7. TerraCover Enhancements

Beyond fixing the iteration bug, TerraCover includes several improvements:

### 7.1 Comprehensive Logging

TerraCover generates detailed log files for each AR adjustment process:

```
VT7 Iterative AR Adjustment Log
============================================================
Deforestation Map: /path/to/deforestation.tif
Output File: /path/to/adjusted_density.tif
Max Iterations: 5
Tolerance: 1.00001
VP Years: 10 (output will be converted to annual rate)
============================================================

Initial State:
  MD (Modeled Deforestation):  12,345.67 ha
  AD (Actual Deforestation):   15,000.00 ha
  AR (Adjustment Ratio):       1.215012

Iteration 1:
  MD (Modeled Deforestation):  14,850.23 ha
  AD (Actual Deforestation):   15,000.00 ha
  AR (Adjustment Ratio):       1.010084

Iteration 2:
  MD (Modeled Deforestation):  14,998.45 ha
  AD (Actual Deforestation):   15,000.00 ha
  AR (Adjustment Ratio):       1.000103

============================================================
Final Results:
  Total Iterations: 2
  Final AR: 1.000103
  Converged: Yes
  Annual Conversion: Divided by 10 years
  Output Type: Annual deforestation rate (ha/year per pixel)
============================================================
```

### 7.2 Unified Function Design

TerraCover uses a single `iterative_ar_adjustment()` function that handles both:
- **CNF/HRP Phase**: Uses `deforestation_cnf` for actual deforestation
- **VP Phase**: Uses `expected_deforestation` for projected deforestation

This eliminates code duplication and ensures consistent behavior across phases.

### 7.3 Input Validation

```python
# Validate vp_years
if vp_years is None or vp_years <= 0:
    raise ValueError(f"vp_years must be a positive integer > 0, got: {vp_years}")
```

### 7.4 Proper NoData Handling

TerraCover properly handles NoData values when calculating actual deforestation:

```python
# Get nodata value from raster band
nodata_value = band.GetNoDataValue()

# Create mask to exclude nodata values
if nodata_value is not None:
    valid_mask = (arr5 == 1) & (arr5 != nodata_value)
else:
    valid_mask = (arr5 == 1)
```

---

## 8. Conclusion

### Summary of Findings

The original UDef-ARP implementation contains two critical bugs in the iterative AR adjustment process:

1. **Non-Accumulative Iteration Bug**: The loop always uses the original prediction density array instead of the result from the previous iteration, contradicting the VT0007 methodology specification.

2. **Extra AR Application Bug**: The saving function applies AR to the array again, partially compensating for Bug #1 but introducing its own mathematical incorrectness.

### TerraCover Corrections

TerraCover's implementation:
- ✅ Correctly implements accumulative iteration as specified in VT0007
- ✅ Does not apply AR when saving (array is already adjusted)
- ✅ Provides detailed logging for auditability
- ✅ Includes comprehensive input validation
- ✅ Properly handles NoData values
- ✅ Uses unified function design to prevent code duplication

### Recommendation

Projects using the VT0007 methodology should adopt the TerraCover implementation or apply equivalent corrections to ensure:
- Mathematically correct AR convergence
- Compliance with methodology specifications
- Accurate deforestation predictions for carbon accounting

---

## References

1. **VT0007 Tool**: Unplanned Deforestation Allocation and Risk Mapping Procedure (Verra)
2. **UDef-ARP Original Code**: `allocation_tool.py` (Verra GitHub Repository)
3. **TerraCover Implementation**: `terracover/modules/vt7/adjustment.py`

---

## Status in UDef-ARP v2.11

v2.11 rewrote the AR loop, resolving one of the three issues but leaving the others — and introducing a new one:

| Sub-issue | v2.11 evidence (`allocation_tool.py`) | Status |
|-----------|----------------------------------------|--------|
| (a) Non-accumulative iteration | CNF line 431 and VP line 478 add `prediction_density_arr = new_prediction_density_arr` | **FIXED** |
| (b) Extra AR application when saving | `adjusted_prediction_density_map` line 318 still runs `AR * prediction_density_arr` after the loop | NOT FIXED |
| (c) Annual-rate conversion (VP) | `time` param removed from `execute_workflow_vp` (line 445); VP now calls `adjusted_prediction_density_map` with no division by years | **NEW ISSUE (regression)** |

So v2.11 makes the iteration accumulative (matching TerraCover and VT0007), but still multiplies by AR one extra time when saving, and — unlike **both** the Original and TerraCover — **drops the annual-rate conversion in the VP workflow entirely**, contradicting VT0007's requirement to divide the VP result by the number of years in the BVP.

Note also the **bidirectional-AR bug** (`while AR > 1.00001`, which adjusts only when the model underestimates): v2.11 does **not** fix it — see `VT7_AR_Adjustment_Bug_Fixes.md`. A full cross-document evaluation is in `VT7_UDef-ARP_Version_Comparison_2.11_vs_Original.md` (Sections 9.2 and 12).

---

*Document Version: 1.0*
*Date: February 2026*
*Author: Terra Global Capital*
*Classification: Technical Documentation*
