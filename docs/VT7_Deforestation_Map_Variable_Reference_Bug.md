# VT7 Bug Fix: Variable Reference Error in create_deforestation_map()

## Executive Summary

A critical bug was identified in the `create_deforestation_map()` method of the `ModelEvaluation` class within the original Verra UDef-ARP code. The bug caused incorrect classification of stable forest pixels in the combined deforestation map, potentially affecting model validation results.

**Severity:** High
**Status:** Fixed in TerraCover implementation
**Date Fixed:** December 29, 2024
**Affected Method:** `ModelEvaluation.create_deforestation_map()`

---

## 1. Bug Description

### 1.1 The Problem

In the `create_deforestation_map()` method, the code incorrectly compared a **file path string** (`fmask`) instead of the **NumPy array** (`arr_fmask`) when classifying "Forest at the start of HRP" pixels.

### 1.2 Original Code (Buggy)

```python
def create_deforestation_map(self, fmask, deforestation_cal, deforestation_cnf, out_fn):
    # Read arrays from files
    arr_fmask = image_to_array(fmask)              # fmask is the file PATH
    arr_def_cal = image_to_array(deforestation_cal)
    arr_def_cnf = image_to_array(deforestation_cnf)

    deforestation_arr = np.copy(arr_fmask)

    # Assign deforestation categories
    deforestation_arr[arr_def_cnf == 1] = 3
    deforestation_arr[(arr_def_cnf == 0) & (arr_def_cal == 1)] = 2
    deforestation_arr[(arr_def_cnf == 0) & (arr_def_cal == 0) & (fmask == 1)] = 1
    #                                                           ^^^^^^^^^^^
    #                                                           BUG: 'fmask' is a STRING path!
    #                                                           Should be 'arr_fmask'
```

### 1.3 Corrected Code

```python
def create_deforestation_map(self, fmask, deforestation_cal, deforestation_cnf, out_fn):
    # Read arrays from files
    arr_fmask = image_to_array(fmask)              # Read file to NumPy array
    arr_def_cal = image_to_array(deforestation_cal)
    arr_def_cnf = image_to_array(deforestation_cnf)

    deforestation_arr = np.copy(arr_fmask)

    # Assign deforestation categories
    deforestation_arr[arr_def_cnf == 1] = 3
    deforestation_arr[(arr_def_cnf == 0) & (arr_def_cal == 1)] = 2
    deforestation_arr[(arr_def_cnf == 0) & (arr_def_cal == 0) & (arr_fmask == 1)] = 1
    #                                                           ^^^^^^^^^^^^^
    #                                                           FIXED: Now uses NumPy array
```

---

## 2. Technical Analysis

### 2.1 Why the Bug Occurred

The parameter `fmask` is passed as a **file path string** (e.g., `"/path/to/forest_mask.tif"`). The method correctly reads this file into `arr_fmask` using `image_to_array()`, but then mistakenly uses `fmask` (the string) instead of `arr_fmask` (the array) in the conditional expression.

### 2.2 Python Behavior

When comparing a string to an integer in Python:

```python
>>> "/path/to/mask.tif" == 1
False
```

The comparison always evaluates to `False` because a string can never equal an integer. This means the condition `(fmask == 1)` is **always False**, regardless of the actual pixel values.

### 2.3 NumPy Boolean Indexing

The correct behavior uses NumPy boolean indexing:

```python
>>> import numpy as np
>>> arr_fmask = np.array([[1, 0, 1], [0, 1, 0]])
>>> arr_fmask == 1
array([[ True, False,  True],
       [False,  True, False]])
```

This creates a boolean mask that correctly identifies pixels with value 1.

---

## 3. Impact Analysis

### 3.1 Classification Logic

The `create_deforestation_map()` method creates a combined deforestation review map with three categories:

| Value | Category | Condition | Bug Impact |
|-------|----------|-----------|------------|
| **3** | Deforestation in CNF (T2-T3) | `arr_def_cnf == 1` | ✅ Unaffected |
| **2** | Deforestation in CAL (T1-T2) | `arr_def_cnf == 0 AND arr_def_cal == 1` | ✅ Unaffected |
| **1** | Forest at start of HRP | `arr_def_cnf == 0 AND arr_def_cal == 0 AND arr_fmask == 1` | ❌ **BROKEN** |

### 3.2 Pixel-Level Impact

Consider three pixels with different forest histories:

| Pixel | arr_fmask | arr_def_cal | arr_def_cnf | Expected | With Bug | Fixed |
|-------|-----------|-------------|-------------|----------|----------|-------|
| A | 1 | 0 | 0 | 1 (Stable Forest) | ❌ Not assigned | ✅ 1 |
| B | 1 | 1 | 0 | 2 (Def in CAL) | ✅ 2 | ✅ 2 |
| C | 1 | 0 | 1 | 3 (Def in CNF) | ✅ 3 | ✅ 3 |

**The bug only affected Pixel A** - forest that remained stable throughout both CAL and CNF periods was not properly classified.

### 3.3 Consequences

1. **Incomplete Deforestation Map**: The combined deforestation review map was missing the "Forest at start of HRP" category (value 1). These pixels retained their original value from `arr_fmask` instead of being explicitly assigned.

2. **Underestimated Forest Baseline**: Model evaluation could show an incorrect baseline forest area since stable forest pixels were not explicitly categorized.

3. **Validation Accuracy Issues**: Any validation metrics that depend on correctly identifying stable forest would be affected.

4. **Visual Inspection Problems**: The review map would not clearly show all three categories, making visual quality control more difficult.

5. **Downstream Analysis**: Any analysis using the combined deforestation map as input would receive incomplete data.

---

## 4. Detection and Verification

### 4.1 How to Detect the Bug

The bug can be detected by:

1. **Unique Value Check**: The output deforestation map should contain values {0, 1, 2, 3}. If value 1 is missing or has unexpected count, the bug may be present.

2. **Area Comparison**: Sum of pixels with value 1 should approximately equal: `Total Forest - Deforestation CAL - Deforestation CNF`

3. **Code Inspection**: Check if the third condition uses `arr_fmask` (correct) or `fmask` (buggy).

### 4.2 Verification Commands

```python
import numpy as np
from osgeo import gdal

# Read the deforestation map
ds = gdal.Open("combined_deforestation_map.tif")
arr = ds.ReadAsArray()

# Check unique values
unique, counts = np.unique(arr[arr != nodata], return_counts=True)
print("Values present:", unique)
print("Pixel counts:", counts)

# Value 1 should be present and have significant count
if 1 not in unique:
    print("WARNING: Value 1 (stable forest) is missing - bug may be present!")
```

---

## 5. Code Location

### 5.1 Original Verra Code (Buggy)

**File:** `terracover/modules/vt7/verra_code/UDef-ARP-main/model_evaluation.py`
**Line:** 487

```python
deforestation_arr[(arr_def_cnf == 0) & (arr_def_cal == 0) & (fmask == 1)] = 1
```

### 5.2 TerraCover Implementation (Fixed)

**File:** `terracover/modules/vt7/evaluation.py`
**Line:** 557

```python
deforestation_arr[(arr_def_cnf == 0) & (arr_def_cal == 0) & (arr_fmask == 1)] = 1
```

**File:** `terracover/modules/vt7/evaluation.py`
**Line:** 557

```python
deforestation_arr[(arr_def_cnf == 0) & (arr_def_cal == 0) & (arr_fmask == 1)] = 1
```

---

## 6. Fix Implementation

### 6.1 Change Required

Single character change: `fmask` → `arr_fmask`

**Before:**
```python
deforestation_arr[(arr_def_cnf == 0) & (arr_def_cal == 0) & (fmask == 1)] = 1
```

**After:**
```python
deforestation_arr[(arr_def_cnf == 0) & (arr_def_cal == 0) & (arr_fmask == 1)] = 1
```

### 6.2 Files Modified

| File | Status |
|------|--------|
| `terracover/modules/vt7/evaluation.py` | ✅ Fixed |
| `terracover/modules/vt7/standalone/.../evaluation.py` | ✅ Fixed |
| `verra_code/UDef-ARP-main/model_evaluation.py` | ❌ Original (preserved for reference) |
| `verra_code/UDef-ARP_edited/model_evaluation.py` | ❌ Original (preserved for reference) |

---

## 7. Testing Recommendations

### 7.1 After Applying the Fix

1. **Re-run Model Evaluation**: Execute model evaluation on existing projects to generate corrected deforestation review maps.

2. **Verify Forest Classification**: Check that value 1 (forest at start of HRP) is present in output maps:
   ```python
   unique_values = np.unique(deforestation_map)
   assert 1 in unique_values, "Value 1 (stable forest) should be present"
   ```

3. **Compare Results**: Compare baseline forest area statistics before and after the fix.

4. **Visual Inspection**: Visually inspect the combined deforestation map to ensure all three categories are properly represented with distinct colors.

### 7.2 Test Case

```python
import numpy as np

def test_create_deforestation_map():
    # Create test arrays
    arr_fmask = np.array([[1, 1, 1, 0],
                          [1, 1, 1, 0],
                          [1, 1, 0, 0]])

    arr_def_cal = np.array([[0, 1, 0, 0],
                            [0, 0, 1, 0],
                            [0, 0, 0, 0]])

    arr_def_cnf = np.array([[0, 0, 0, 0],
                            [1, 0, 0, 0],
                            [0, 1, 0, 0]])

    # Apply classification logic
    deforestation_arr = np.copy(arr_fmask)
    deforestation_arr[arr_def_cnf == 1] = 3
    deforestation_arr[(arr_def_cnf == 0) & (arr_def_cal == 1)] = 2
    deforestation_arr[(arr_def_cnf == 0) & (arr_def_cal == 0) & (arr_fmask == 1)] = 1

    # Verify results
    expected = np.array([[1, 2, 1, 0],
                         [3, 1, 2, 0],
                         [1, 3, 0, 0]])

    assert np.array_equal(deforestation_arr, expected), "Classification failed"
    assert 1 in deforestation_arr, "Value 1 (stable forest) must be present"
    print("Test passed!")

test_create_deforestation_map()
```

---

## 8. Related Improvements

While fixing this bug, several other improvements were made to the `ModelEvaluation` class:

1. **Removed PyQt Dependency**: Eliminated dependency on `QObject` and `pyqtSignal`, making the class standalone.

2. **Updated Seaborn API**: Changed deprecated `sns.set()` to `sns.set_theme()`.

3. **Eliminated Code Duplication**: Removed duplicate utility methods by using global functions.

4. **Enhanced Documentation**: Added comprehensive docstrings to all methods.

5. **Workflow Integration**: Created `evaluate_testing_stage()` wrapper function for easy integration.

6. **Missing Bins Handling**: Integrated `calculate_missing_bins_rf()` to handle missing modeling regions.

---

## 9. Lessons Learned

### 9.1 Variable Naming

The bug could have been prevented with clearer variable naming:

```python
# Better naming convention
def create_deforestation_map(self, fmask_path, deforestation_cal_path, ...):
    fmask_array = image_to_array(fmask_path)
    #     ^^^^^                      ^^^^^
    #     Clearly an array           Clearly a path
```

### 9.2 Type Hints

Adding type hints would make the expected types explicit:

```python
def create_deforestation_map(
    self,
    fmask: str,  # File path
    deforestation_cal: str,  # File path
    deforestation_cnf: str,  # File path
    out_fn: str  # Output file path
) -> np.ndarray:
```

### 9.3 Code Review

This type of bug is easily caught by:
- Static type checkers (mypy, pyright)
- Code review focusing on variable usage
- Unit tests that verify output values

---

## 10. References

- **Original Bug Location:** Verra UDef-ARP `model_evaluation.py`, line 487
- **VT0007 Methodology Documentation**
- **TerraCover VT7 Implementation Guide**
- **Bug Discovery Session:** December 29, 2024

---

## 11. Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | Dec 29, 2024 | TerraCover Team | Initial bug fix |
| 1.1 | Feb 2025 | TerraCover Team | Documentation created |

---

## 12. Status in UDef-ARP v2.11

Verra's later release, **UDef-ARP v2.11**, does **not** fix this bug — the offending line is identical to the Original.

**Original** (`UDef-ARP-main/model_evaluation.py`, line 487):
```python
deforestation_arr[(arr_def_cnf == 0) & (arr_def_cal == 0) & (fmask == 1)] = 1
```

**v2.11** (`UDef-ARP-main 2.11/model_evaluation.py`, line 477):
```python
deforestation_arr[(arr_def_cnf == 0) & (arr_def_cal == 0) & (fmask == 1)] = 1
```

Both compare the **string path** `fmask` against the integer `1`, which is always `False`, so the "Forest at start of HRP" category (value 1) is never assigned. v2.11 still reads `arr_fmask = self.image_to_array(fmask)` earlier but references the wrong variable in the comparison, exactly as the Original does.

**Verdict: NOT FIXED in v2.11.** Only the TerraCover implementation uses `arr_fmask == 1`.

---

*Document generated for TerraCover VT0007 Module - Bug Fix Documentation*
