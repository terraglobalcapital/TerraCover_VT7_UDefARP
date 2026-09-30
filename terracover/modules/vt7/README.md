# VT7 Package - Modular Structure

This package contains the modular implementation of the VT7 (Vulnerability Mapping Tool 7) methodology for forest vulnerability mapping and deforestation risk assessment.

## Package Structure

```
vt7/
├── __init__.py                  # Package initialization and exports
├── utils.py                     # Utility functions (24 KB)
├── folder_structure.py          # Folder management and inputs generation (18 KB)
├── geometric_classification.py  # NRT and geometric classification (13 KB)
├── frequency_analysis.py        # Frequency tables and tabulation (18 KB)
├── adjustment.py                # Adjustment ratio calculations (9.2 KB)
├── evaluation.py                # Model evaluation and analysis (43 KB)
├── workflow.py                  # Main workflow orchestration (29 KB)
└── README.md                    # This file
```

## Module Descriptions

### utils.py
**Purpose**: Core utility functions for raster/vector processing

**Functions**:
- `image_to_array()`: Read raster to numpy array
- `array_to_image()`: Write numpy array to raster
- `apply_mask_to_raster()`: Apply mask to raster with flexible outside values
- `vector_to_raster()`: Convert vector to raster with compression
- `admin_divisions_to_raster()`: Rasterize administrative divisions with consecutive IDs
- `convert_expression_to_numpy()`: Convert map algebra expressions to numpy
- `raster_calculator()`: Execute raster calculations
- `euclidean_distance()`: Calculate Euclidean distance using GDAL
- `create_jnr_constrained_mask()`: Create JNR-constrained exclusions mask
- `replace_ref_system()`: Fix reference system in RST files

### folder_structure.py
**Purpose**: Manage VT7 folder structure

**Classes**:
- `VT7FolderStructure`: Manages the VT7 folder hierarchy
  - Creates base folders (Testing Stage, Application Stage)
  - Creates model-specific folders on demand

### geometric_classification.py
**Purpose**: NRT calculation and geometric classification methods

**Functions**:
- `nrt_calculation()`: Calculate Negligible Risk Threshold with histogram analysis
- `geometric_classification()`: Benchmark model geometric classification
- `kmeans_classification_alternative()`: Alternative model classification, k-means with k = n_classes over the ETP. Geometric intervals are prescribed for the benchmark, where the surface is distance from the forest edge; over an empirical vulnerability surface they leave the lowest classes empty or near-empty, so a relative frequency cannot be estimated for them.

### frequency_analysis.py
**Purpose**: Frequency analysis and tabulation for vulnerability mapping

**Functions**:
- `tabulation_bin_id()`: Create tabulation of bin IDs with administrative divisions
- `calculate_missing_bins_rf()`: Calculate relative frequency for missing bins
- `create_relative_frequency_table()`: Generate relative frequency tables with statistics
- `calculate_missing_bins_rf()`: Substitute a frequency for modeling regions absent from the
  fitting phase — the zone's area-weighted average where the zone exists, an interpolation
  along the vulnerability gradient where the whole zone is absent
- `create_fit_density_map()`: Create fitted density maps from relative frequencies

### adjustment.py
**Purpose**: Adjustment ratio calculations and iterative adjustments

**Functions**:
- `calculate_adjustment_ratio_cnf()`: Calculate AR for confirmation period
- `adjusted_prediction_density_array()`: Apply AR to density array
- `iterative_ar_adjustment()`: Iterative AR adjustment with convergence checks

### evaluation.py
**Purpose**: Model evaluation and performance analysis

**Classes**:
- `ModelEvaluation`: Comprehensive model evaluation class
  - Voronoi-based spatial sampling
  - Statistical analysis and metrics
  - Visualization and reporting
  - Plot generation for evaluation results (PNG plus an interactive HTML plot with per-cell
    hover, written when plotly is available)
  - Per-cell statistics (MedAE, MAE) on values normalised to the nominal grid area, since the
    exclusion mask leaves the cells unequal in area; aggregate statistics (Agreement,
    Difference, IoU) on raw hectares, since they sum over cells rather than comparing them

**Functions**:
- `evaluate_testing_stage()`: Evaluate testing stage model performance

### workflow.py
**Purpose**: Main workflow orchestration for VT7 analysis

**Functions**:
- `run_testing_stage()`: Execute testing stage for benchmark or alternative models
  - Fitting phase: NRT calculation, geometric classification, frequency analysis
  - Prediction phase: Density map creation, AR adjustment

- `run_application_stage()`: Execute application stage for models
  - Fitting phase: NRT calculation, geometric classification, frequency analysis
  - Prediction phase: Density map creation

## Usage Example

### Complete Workflow (Recommended)

For running the complete VT7 workflow with GUI support, data conversions, and progress tracking:

```python
from terracover.modules.udef_arp import udef_arp

# Run complete VT7 workflow
results = udef_arp(
    fcbm_file="path/to/fcbm.tif",
    output_vt7_folder="path/to/output",
    jnr_with_exclusions_mask="path/to/jnr_mask.tif",
    admin_divisions="path/to/admin.shp",
    area_of_interest="path/to/aoi_binary_mask.tif",  # Binary mask: 1=analysis area, 0=outside
    expected_deforestation=29376,
    workflow_stages=["BCM Calibration (CAL)", "BCM Confirmation (CNF)",
                     "BCM Evaluation CAL", "BCM Evaluation CNF"]
)
```

### Advanced Usage - Individual Stages

```python
from terracover.modules.vt7 import (
    VT7FolderStructure,
    run_testing_stage,
    run_application_stage,
    evaluate_testing_stage
)

# 1. Setup folder structure
folders = VT7FolderStructure("path/to/output")
folders.create_testing_models(bcm_testing=True)

# 2. Run testing stage (VT7 inputs are generated on-demand)
testing_results = run_testing_stage(
    folders=folders,
    jnr_with_exclusions_mask="path/to/mask.tif",
    admin_divisions="path/to/admin_raster.tif",
    n_classes=30,
    max_iterations=5
)

# 3. Evaluate model
evaluation = evaluate_testing_stage(
    folders=folders,
    fcbm_file="path/to/fcbm.tif",
    jnr_lb_full_areas="path/to/aoi_binary_mask.tif",  # Binary mask for Voronoi generation
    jnr_with_exclusions_mask="path/to/mask.tif",
    jnr_value=1,  # Value for analysis area in binary mask
    model_type='benchmark',
    evaluation_grid_area=100000
)

# 4. Run application stage
application_results = run_application_stage(
    folders=folders,
    admin_divisions="path/to/admin_raster.tif",
    nrt=testing_results['nrt'],
    expected_deforestation=29376,
    model_type='benchmark'
)
```

## Migration from Original udef_arp.py

The original monolithic `udef_arp.py` file (3455 lines) has been reorganized into this modular structure for better maintainability. The original file is backed up as `udef_arp_backup.py`.

### What Changed:
- **Before**: Single 3455-line file with all functions
- **After**: 7 focused modules with clear responsibilities
- **Main Entry Point**: Use `terracover.modules.udef_arp.udef_arp()` for complete workflow
- **Individual Stages**: Use functions from `terracover.modules.vt7` for fine-grained control

### Compatibility:
- The main execution script `udef_arp.py` has been updated to use the new package
- All functionality remains the same
- Parameters and return values are unchanged
- Existing projects can be updated by changing imports

## Development Guidelines

### Adding New Features
1. Identify the appropriate module based on functionality
2. Add function to the module with proper documentation
3. Update `__init__.py` to export the function if it's part of the public API
4. Update this README with the new function

### Code Organization Principles
- **utils.py**: Stateless utility functions
- **folder_structure.py**: Folder and file management
- **geometric_classification.py**: Classification algorithms
- **frequency_analysis.py**: Statistical analysis and tabulation
- **adjustment.py**: Numerical adjustments and iterations
- **evaluation.py**: Model evaluation and visualization
- **workflow.py**: High-level orchestration only

### Testing
All modules pass Python syntax validation:
```bash
python -m py_compile terracover/modules/vt7/*.py
```

## Bug Fixes and Improvements

### Critical Bug Fixes
The VT7 module includes several critical bug fixes compared to the original Verra UDef-ARP implementation:

#### 1. AR Bidirectional Adjustment Bug Fix
**Location**: `adjustment.py:175`
**Issue**: The iterative Adjustment Ratio (AR) convergence loop only executed when AR > 1 (model underestimates). When AR < 1 (model overestimates), no adjustments were applied, leaving density maps with inflated values.

**Fix Applied**: Changed loop condition to handle both directions:
```python
# Before (broken):
while AR > tolerance and iteration_count < max_iterations:

# After (fixed):
inverse_tolerance = 1.0 / tolerance
while (AR > tolerance or AR < inverse_tolerance) and iteration_count < max_iterations:
```

#### 2. AR Implementation Bug (Non-Accumulative Iterations)
**Location**: Original UDef-ARP `allocation_tool.py`
**Issue**: The iterative AR adjustment incorrectly used the original prediction density array in every iteration instead of building upon previous results, violating the VT0007 methodology specification.

**Fix Applied**: TerraCover implements accumulative iteration as specified:
```python
# Correct: Uses result from previous iteration
current_density_arr = adjusted_prediction_density_array(
    current_density_arr,  # Updated each iteration
    risk30,
    AR
)
```

#### 3. Deforestation Map Variable Reference Bug
**Location**: `evaluation.py:557`
**Issue**: In `create_deforestation_map()`, the code incorrectly compared a file path string (`fmask`) instead of the NumPy array (`arr_fmask`) when classifying stable forest pixels.

**Fix Applied**: Simple variable reference correction:
```python
# Before (buggy):
deforestation_arr[(arr_def_cnf == 0) & (arr_def_cal == 0) & (fmask == 1)] = 1

# After (fixed):
deforestation_arr[(arr_def_cnf == 0) & (arr_def_cal == 0) & (arr_fmask == 1)] = 1
```

#### 4. Missing Vulnerability Zones Bug
**Location**: `frequency_analysis.py`
**Issue**: When entire vulnerability zones existed in the prediction phase but were absent from the fitting phase, NaN values propagated through calculations, causing AR to become NaN and preventing proper adjustment.

**Fix Applied**: Detect and handle missing vulnerability zones by assigning `Average Deforestation = 0`:
```python
missing_v_zones_set = set(missing_v_zone) - fitting_v_zones
if missing_v_zones_set:
    print(f"Warning: {len(missing_v_zones_set)} vulnerability zone(s) have no data in fitting phase")
    missing_bins_df = missing_bins_df.fillna(0)
```

#### 5. Geometric Classification Distribution Bug
**Location**: `geometric_classification.py`
**Issue**: Original implementation created n_classes+1 total classes instead of the user-specified n_classes, and lacked complete coverage of the classification range.

**Fix Applied**: 
- Benchmark model: Uses `(n_classes - 1)` for ratio calculation to account for Class 1 beyond NRT
- Alternative model: Implements normalized deltas to guarantee exact range coverage

### Methodological Improvements

#### 1. Dual-Mask Model Evaluation System
Enhanced model evaluation with separate masks for Voronoi generation vs. exclusion application:
- `mask_voronoi`: Full jurisdictional area for continuous grid generation
- `mask_exclusions`: Area with exclusions for final statistics
- Results in more statistically robust samples

#### 2. Enhanced Data Type Safety
- Uses int32 instead of int16 for modeling region IDs (supports larger administrative division IDs)
- Explicit NoData value handling throughout the pipeline
- Comprehensive input validation

#### 3. Improved Output Formats
- Excel output with proper number formatting
- Detailed iteration logging for transparency
- Optional relative frequency maps for visualization

## Version History

### Version 1.0.0 (2025-12-31)
- Initial modular refactoring from monolithic udef_arp.py
- Created 7 focused modules
- Established clear separation of concerns
- Added comprehensive documentation
- Verified syntax and imports

### Version 1.1.0 (2026-02-01)
- Fixed critical AR bidirectional adjustment bug
- Corrected AR implementation to follow VT0007 methodology
- Fixed deforestation map variable reference bug
- Added missing vulnerability zones handling
- Corrected geometric classification distribution
- Implemented dual-mask model evaluation system
- Enhanced NoData handling throughout pipeline
- Improved output formats and logging

## Author

David Montoya (david.montoya@terraglobalcapital.com)
Terra Global Capital LLC
2025
