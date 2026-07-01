# VT7 Geometric Distribution Analysis

## Bug Report: Geometric Classification Implementation Differences

**Document Version:** 1.0
**Date:** February 2025
**Author:** TerraCover Development Team

---

## Executive Summary

This document describes a critical bug identified in the original Verra UDef-ARP implementation of the geometric classification algorithm. The bug affects both the Benchmark Model (`geometric_classification`) and the Alternative Model (`geometric_classification_alternative`), resulting in incorrect class distribution and inconsistent behavior with user-specified parameters.

The TerraCover implementation provides corrected versions of these algorithms that properly respect the user-specified number of classes and ensure complete coverage of the classification space.

---

## Table of Contents

1. [Background](#1-background)
2. [Bug Analysis: Benchmark Model](#2-bug-analysis-benchmark-model)
3. [Bug Analysis: Alternative Model](#3-bug-analysis-alternative-model)
4. [Corrected Implementation](#4-corrected-implementation)
5. [Mathematical Proof](#5-mathematical-proof)
6. [Impact Assessment](#6-impact-assessment)
7. [Recommendations](#7-recommendations)
8. [Comparison with UDef-ARP v2.11](#8-comparison-with-udef-arp-v211)

---

## 1. Background

### 1.1 VT0007 Methodology Overview

The VT0007 methodology (Unplanned Deforestation Allocated Risk Proxy) uses geometric classification to stratify forest areas based on their vulnerability to deforestation. The classification creates risk classes where:

- **Higher class numbers** indicate **higher risk** (closer to forest edge or higher ETP values)
- **Lower class numbers** indicate **lower risk** (farther from forest edge or lower ETP values)
- **Class 1** represents areas beyond the Negligible Risk Threshold (NRT) in the Benchmark Model

### 1.2 Geometric Series Principle

The geometric classification divides a range [LL, UL] into n classes using a geometric series, where each class width follows the ratio:

```
r = (LL/UL)^(1/k)
```

Where `k` determines how many intervals are created within the range.

---

## 2. Bug Analysis: Benchmark Model

### 2.1 Original Verra Implementation

**File:** `UDef-ARP-main/vulnerability_map.py`
**Function:** `geometric_classification()`

```python
# Original Verra code
def geometric_classification(self, in_fn, NRT, n_classes):
    # ...
    LL = int(in_ds.GetGeoTransform()[1])  # Pixel size (e.g., 30m)
    UL = NRT = int(NRT)                    # e.g., 5000m
    n_classes = int(n_classes)             # e.g., 30

    # BUG: Uses n_classes directly instead of (n_classes - 1)
    r = np.power(LL / UL, 1/n_classes)

    # Creates n_classes intervals
    class_array = np.array([[i, i + 1] for i in range(n_classes)])
    x = np.power(r, class_array)
    risk_class = np.multiply(UL, x)

    # Class 1 assigned to areas >= NRT (beyond threshold)
    mask_arr[arr >= NRT] = 1

    # Classes 2-30 assigned within NRT
    # ... hardcoded assignments for 29 classes ...
```

### 2.2 The Bug

When `n_classes=30`:

1. The formula `r = (LL/UL)^(1/30)` creates a ratio for **30 intervals**
2. Class 1 is assigned to areas beyond NRT (implicit, not counted in the 30)
3. Classes 2-30 are assigned within NRT (29 classes explicitly coded)
4. **Result: 31 effective classes** (1 beyond NRT + 30 within NRT)

**Problem:** The user specifies `n_classes=30` expecting exactly 30 total classes, but receives 31.

### 2.3 Visual Representation

```
Original Verra (Bug):
User specifies: n_classes = 30
Actual result:  31 classes

[Class 1: Beyond NRT] + [Class 2...Class 31: Within NRT using 30 intervals]
         ^                            ^
    Not counted in              30 intervals from
    n_classes formula           r = (LL/UL)^(1/30)
```

### 2.4 Additional Issues

1. **Hardcoded class assignments:** The original code hardcodes 29 class assignments (lines 135-168), making it inflexible for different `n_classes` values
2. **Off-by-one error:** The geometric ratio calculation doesn't account for Class 1 being reserved for "beyond NRT"

---

## 3. Bug Analysis: Alternative Model

### 3.1 Original Verra Implementation

**File:** `UDef-ARP-main/vulnerability_map.py`
**Function:** `geometric_classification_alternative()`

```python
# Original Verra code
def geometric_classification_alternative(self, in_fn, n_classes, mask, fmask):
    # ...
    # Rescale ETP map to [1.0, 2.0] range
    arr_rescale = 1 + arr * 1 / max_value

    LL = int(1)
    UL = int(2)
    n_classes = int(n_classes)

    # Same ratio formula
    r = np.power(LL / UL, 1 / n_classes)

    # BUG: Reversed array order
    class_array = np.array([[i, i + 1] for i in range(n_classes-1, -1, -1)])

    x = np.power(r, class_array)
    risk_class = np.multiply(UL, x)

    # Hardcoded 30 class assignments...
```

### 3.2 The Bug

1. **Incomplete range coverage:** The geometric series may not perfectly cover the [1, 2] range due to floating-point precision and the reversed array construction
2. **Hardcoded assignments:** 30 classes are hardcoded (lines 230-264), preventing flexibility
3. **Potential gaps:** The class boundaries may have small gaps or overlaps due to the non-normalized approach

### 3.3 Mathematical Issue

The original approach computes class boundaries as:
```
risk_class[i] = UL × r^(class_array[i])
```

This does **not** guarantee that:
- The sum of class widths equals exactly (UL - LL)
- All values in [1, 2] are assigned to exactly one class

---

## 4. Corrected Implementation

### 4.1 TerraCover Benchmark Model

**File:** `terracover/modules/vt7/geometric_classification.py`
**Function:** `geometric_classification()`

```python
def geometric_classification(in_fn, out_fn, NRT, n_classes):
    # ...
    LL = int(in_ds.GetGeoTransform()[1])
    UL = NRT = int(NRT)
    n_classes = int(n_classes)

    # CORRECTED: Account for Class 1 (beyond NRT)
    n_classes_within_nrt = n_classes - 1

    # Ratio calculated for (n_classes - 1) intervals
    r = np.power(LL / UL, 1 / n_classes_within_nrt)

    # Create boundaries for classes within NRT
    class_array = np.array([[i, i + 1] for i in range(n_classes_within_nrt)])
    x = np.power(r, class_array)
    risk_class = np.multiply(UL, x)

    # Class 1: Beyond NRT
    mask_arr[arr >= NRT] = 1

    # Classes 2 to n_classes: Within NRT (using loop for flexibility)
    for i in range(n_classes_within_nrt - 1, -1, -1):
        upper_bound = risk_class[i][0]
        lower_bound = risk_class[i][1]
        mask_arr[(arr < upper_bound) & (arr >= lower_bound)] = i + 2
```

**Key Corrections:**
1. Uses `n_classes - 1` for the ratio calculation
2. Flexible loop instead of hardcoded assignments
3. Exact `n_classes` total classes as specified by user

### 4.2 TerraCover Alternative Model

**File:** `terracover/modules/vt7/geometric_classification.py`
**Function:** `geometric_classification_alternative()`

```python
def geometric_classification_alternative(in_fn, n_classes, mask, fmask, out_fn):
    # ...
    # Rescale to [1.0, 2.0]
    arr_rescale = 1 + arr * 1 / max_value

    LL = int(1)
    UL = int(2)
    n_classes = int(n_classes)

    r = np.power(LL / UL, 1 / n_classes)

    # CORRECTED: Generate normalized deltas
    raw_deltas = r ** np.arange(n_classes)

    # Normalize to ensure exact coverage of [LL, UL]
    deltas = (UL - LL) * raw_deltas / raw_deltas.sum()

    # Create exact class edges via cumulative sum
    edges = LL + np.cumsum(np.insert(deltas, 0, 0))

    # Reshape to [upper, lower] boundary pairs
    risk_class = np.column_stack((edges[1:], edges[:-1]))

    # Flexible classification loop
    for i in range(n_classes - 1, -1, -1):
        upper_bound = risk_class[i][0]
        lower_bound = risk_class[i][1]
        class_value = i + 1
        mask_arr[(masked_values < upper_bound) & (masked_values >= lower_bound)] = class_value
```

**Key Corrections:**
1. **Normalized deltas:** Guarantees class widths sum exactly to (UL - LL)
2. **Cumulative sum edges:** Creates precise, non-overlapping boundaries
3. **Complete coverage:** Every value in [1, 2] maps to exactly one class
4. **Flexible loop:** Works with any `n_classes` value

---

## 5. Mathematical Proof

### 5.1 Benchmark Model Correction

**Given:**
- `n_classes = 30` (total classes desired)
- Class 1 = beyond NRT
- Classes 2-30 = within NRT (29 classes)

**Original (incorrect):**
```
r = (LL/UL)^(1/30)
Creates 30 intervals + Class 1 = 31 total classes
```

**Corrected:**
```
r = (LL/UL)^(1/29)
Creates 29 intervals + Class 1 = 30 total classes ✓
```

### 5.2 Alternative Model Normalization

**Goal:** Divide [1, 2] into `n` classes with geometrically decreasing widths.

**Original approach:**
```
width[i] = UL × r^(i+1) - UL × r^i = UL × r^i × (r - 1)
Sum of widths ≠ (UL - LL) in general
```

**Corrected approach:**
```
raw_delta[i] = r^i
normalized_delta[i] = (UL - LL) × raw_delta[i] / sum(raw_deltas)
Sum of normalized_deltas = (UL - LL) exactly ✓
```

**Proof:**
```
sum(normalized_deltas) = (UL - LL) × sum(raw_deltas) / sum(raw_deltas)
                       = (UL - LL) ✓
```

---

## 6. Impact Assessment

### 6.1 Effects of the Original Bug

| Aspect | Impact |
|--------|--------|
| **Class count mismatch** | User expects 30 classes, receives 31 |
| **Frequency table errors** | Statistics may be calculated for wrong number of classes |
| **Adjustment ratio errors** | AR calculations may be affected by extra class |
| **Model comparison** | Benchmark vs Alternative comparison may be skewed |
| **Documentation mismatch** | Reports may show incorrect class definitions |

### 6.2 Scenarios Affected

1. **Benchmark Testing Stage:** Incorrect class boundaries affect frequency tables
2. **Benchmark Application Stage:** Vulnerability map has extra class
3. **Alternative Model:** Potential gaps in classification may leave pixels unclassified
4. **Model Evaluation:** Comparison metrics may be affected

---

## 7. Recommendations

### 7.1 For New Projects

Use the corrected TerraCover implementation which:
- Respects user-specified `n_classes` exactly
- Provides complete, gap-free classification
- Uses flexible loops instead of hardcoded values

### 7.2 For Existing Projects

If projects were processed with the original Verra code:
1. **Document the discrepancy:** Note that 31 classes were used instead of 30
2. **Consider reprocessing:** If accuracy is critical, reprocess with corrected code
3. **Verify outputs:** Check that frequency tables and AR calculations are consistent

### 7.3 Validation Steps

To verify correct implementation:
1. Count unique classes in output vulnerability map
2. Verify class boundaries sum to expected range
3. Check that no pixels are left unclassified within the study area

---

## 8. Comparison with UDef-ARP v2.11

Sections 2–5 contrast the TerraCover fix with the original Verra reference (`UDef-ARP-main`). Verra later released **UDef-ARP v2.11** (`UDef-ARP-main 2.11`), which rewrote parts of `geometric_classification`. This section compares **all three** implementations and clarifies whether v2.11 resolves the off-by-one bug.

### 8.1 Benchmark Model — Three-Way Behavior (n_classes = 30)

All three compute `risk_class[i] = UL·r^[i, i+1]`, where `LL` = pixel resolution, `UL` = NRT. What differs is the exponent and how the intervals are assigned:

| Aspect | Original | v2.11 | TerraCover |
|--------|----------|-------|------------|
| Ratio `r` | `(LL/UL)^(1/n)` | `(LL/UL)^(1/n)` | **`(LL/UL)^(1/(n−1))`** |
| Geometric intervals | n | n | **n−1** |
| Class assignment | 29 **hardcoded** lines → classes 2–30 | **loop** → classes 2..**31** | **loop** → classes 2–30 |
| Boundary clamp | none | `risk_class[n−1][1]=LL`, `[0][0]=NRT` | implicit (n−1 lands on LL) |
| Coverage of high-risk band `[LL, UL·r^(n−1))` | **NOT covered** (a gap) | covered (as class 31) | covered (as class 30) |
| Total classes emitted | classes 1–30 **plus stray raw distances** in the gap | **31** classes (off-by-one) | **30** classes (exact) |
| Arbitrary `n` support | **n=30 only** (hardcoded) | any n | any n |

**Key clarification on the "31 classes" description.** The 31-class outcome described in Section 2.2 is precisely the behavior of **v2.11's looped implementation**: its loop `for i in range(n_classes)` assigns classes `2..n+1`, and the clamp closes the bottom edge, so `n=30` yields 31 total classes. The **older Original** behaves differently: its 29 hardcoded lines assign only classes 2–30, leaving the highest-risk sliver `[LL, UL·r²⁹)` **unclassified** — those near-edge pixels keep raw distance values, so the map is incomplete rather than simply over-counted. Both symptoms share the **same root cause**: the ratio uses `1/n` instead of `1/(n−1)`.

**Did v2.11 fix the off-by-one bug?** **No.** v2.11 keeps the incorrect `1/n` exponent, so it still does not honor the user-requested class count (it emits 31 instead of 30). What v2.11 changed is the *symptom*, not the *cause*: it eliminated the Original's coverage gap (via the loop + clamp), producing a cleaner, fully-classified map — but with one class too many. Only TerraCover's `1/(n−1)` correction yields exactly `n` classes with gap-free coverage.

### 8.2 Alternative Model — Three-Way Formulas

Input is the empirical vulnerability map `[0,1]` rescaled to `[1,2]` (`LL=1`, `UL=2`); high risk = value near 2.

| Aspect | Original | v2.11 | TerraCover |
|--------|----------|-------|------------|
| Ratio `r` | `(LL/UL)^(1/n) = (½)^(1/n)` | **`(UL/LL)^(1/n) = 2^(1/n)`** (inverse) | `(LL/UL)^(1/n) = (½)^(1/n)` |
| Boundary formula | `UL·r^k` | `LL+(UL−LL·r^k) = 3 − r^k` | normalized cumulative deltas |
| Width distribution | **wide at HIGH risk** | wide at LOW risk (fine at high) | wide at LOW risk (fine at high) |
| Coverage sum | geometric partition | reflected geometric | **exactly `UL−LL`, gap-free** |
| `max_value` | `GetMaximum()`, no fallback | `GetMaximum()` + `np.max` fallback | **`np.max` of valid data, excludes NoData** |

**v2.11 and TerraCover produce identical boundaries despite reciprocal `r`.** Although v2.11 uses `r₂ = 2^(1/n)` and TerraCover uses `r_T = (½)^(1/n) = 1/r₂`, the reciprocal ratio is exactly compensated by v2.11's reflected formula (`3 − r^k`) and TerraCover's cumulative construction. Both reduce to the same edge set:

```
v2.11:      edge_k = 3 − r₂^k        = 3 − 2^(k/n)
TerraCover: edge_m = 3 − 2·r_T^m     = 3 − 2^((n−m)/n)   →  same set { 3 − 2^(k/n) }
```

For n=5 both give `{1, 1.2589, 1.4843, 1.6805, 1.8513, 2}`. The **Original** instead uses `UL·r^k = 2^(k/n)`, giving the *mirror-image* set `{1, 1.1487, 1.3195, 1.5157, 1.7411, 2}` — reflected about 1.5, which puts wide classes at the **high-risk** end (coarser discrimination where deforestation is most likely).

So for the alternative model, **v2.11 already matches TerraCover's class distribution**; TerraCover's remaining advantages are robustness — guaranteed gap-free normalization (no floating-point drift) and NoData-aware `max_value` computation (v2.11 mis-rescales when raster metadata is stale or NoData is present).

### 8.3 Bug Resolution Status in v2.11

| Model | Bug | Original | v2.11 | TerraCover |
|-------|-----|----------|-------|------------|
| Benchmark | Off-by-one class count | Not fixed (gap at high risk) | **Not fixed** (31 classes; symptom cleaner) | **Fixed** (exactly n) |
| Alternative | Distribution direction | Wrong (wide at high risk) | Corrected (matches TerraCover) | Correct |
| Alternative | Gap-free coverage | Not guaranteed | Not guaranteed (float drift) | **Guaranteed** (normalized) |
| Alternative | NoData-aware rescaling | No | Partial (fallback only) | **Yes** |
| Both | Flexible `n` (no hardcoding) | No (n=30 only) | Yes | Yes |

A full cross-document evaluation of v2.11 is available in `VT7_UDef-ARP_Version_Comparison_2.11_vs_Original.md` (Sections 9.1 and 13).

---

## Appendix A: Code Comparison Summary

| Feature | Verra Original | TerraCover Corrected |
|---------|---------------|---------------------|
| Benchmark ratio formula | `(LL/UL)^(1/n_classes)` | `(LL/UL)^(1/(n_classes-1))` |
| Benchmark total classes | n_classes + 1 | n_classes (exact) |
| Alternative normalization | None | Normalized to range |
| Class assignment | Hardcoded 30 classes | Flexible loop |
| Gap-free guarantee | No | Yes |

---

## Appendix B: File References

- **Original Verra code:** `vt7/verra_code/UDef-ARP-main/vulnerability_map.py`
- **Corrected TerraCover code:** `vt7/geometric_classification.py`
- **Main module:** `modules/udef_arp.py`

---

*Document generated by TerraCover Development Team*
