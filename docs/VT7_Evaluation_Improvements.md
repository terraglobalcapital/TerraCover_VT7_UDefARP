# TerraCover Model Evaluation: Methodological Improvements over UDef-ARP

## Executive Summary

This document describes the methodological improvements implemented in TerraCover's model evaluation module (`evaluation.py`) compared to the original Verra UDef-ARP implementation. The primary enhancement is the introduction of a **dual-mask system** for Thiessen polygon generation, which provides more statistically robust sample selection and proper handling of exclusion zones.

---

## Table of Contents

1. [Introduction](#introduction)
2. [Key Architectural Difference: Dual-Mask System](#key-architectural-difference-dual-mask-system)
3. [Detailed Code Comparison](#detailed-code-comparison)
   - [Mask Polygon Creation](#1-mask-polygon-creation)
   - [Thiessen Polygon Generation](#2-thiessen-polygon-generation)
   - [Edge Cell Filtering](#3-edge-cell-filtering)
   - [Exclusion Handling](#4-exclusion-handling)
4. [Impact on Sample Count](#impact-on-sample-count)
5. [Statistical Implications](#statistical-implications)
6. [Additional Enhancements](#additional-enhancements)
7. [Conclusion](#conclusion)

---

## Introduction

The VT7 (Verra Tool 7) UDef-ARP (Unplanned Deforestation Allocation and Risk Mapping Procedure) methodology requires model evaluation using Thiessen (Voronoi) polygon grids. The evaluation compares predicted deforestation against actual deforestation within grid cells to assess model accuracy.

TerraCover implements an improved version of this methodology that addresses fundamental issues with how exclusion zones (protected areas, water bodies, leakage belts, etc.) affect the evaluation grid generation.

---

## Key Architectural Difference: Dual-Mask System

### UDef-ARP Approach (Single Mask)

The original UDef-ARP implementation uses a **single mask** for the entire evaluation process:

```
Input: Single Jurisdictional Mask (with or without exclusions)
    ↓
1. Polygonize mask
2. Select largest polygon only
3. Generate Voronoi grid
4. Filter edge cells (99.9% threshold)
5. Calculate zonal statistics
    ↓
Output: Evaluation Results
```

### TerraCover Approach (Dual Mask)

TerraCover introduces a **dual-mask system** that separates concerns:

```
Input: Two Masks
    ├── mask_voronoi: Full jurisdictional area (NO exclusions)
    └── mask_exclusions: Jurisdictional area WITH exclusions applied
    ↓
1. Polygonize BOTH masks separately
2. Generate Voronoi grid using mask_voronoi (continuous geometry)
3. Filter edge cells using mask_voronoi (99.9% threshold on full area)
4. Apply mask_exclusions to filtered polygons (removes excluded areas)
5. Dissolve fragments back to original Voronoi cell IDs
6. Calculate zonal statistics on final polygons
    ↓
Output: Evaluation Results
```

---

## Detailed Code Comparison

### 1. Mask Polygon Creation

#### UDef-ARP Implementation

**File:** `model_evaluation.py` (lines 122-171)

```python
def create_mask_polygon(self, mask):
    '''
    Create municipality mask polygon
    :param mask: mask of the jurisdiction (binary map)
    '''
    in_ds = gdal.Open(mask)
    in_band = in_ds.GetRasterBand(1)

    # Set up spatial reference
    projection = in_ds.GetProjection().encode('utf-8', 'backslashreplace').decode('utf-8')
    spatial_ref = osr.SpatialReference()
    spatial_ref.ImportFromWkt(projection)

    # Create temporary shapefile for ALL polygons
    temp_layername = "TEMP_POLYGONIZED"
    driver = ogr.GetDriverByName("ESRI Shapefile")
    temp_ds = driver.CreateDataSource(temp_layername + ".shp")
    temp_layer = temp_ds.CreateLayer(temp_layername, srs=spatial_ref)
    gdal.Polygonize(in_band, in_band, temp_layer, -1, [], callback=None)

    # SELECT ONLY THE LARGEST POLYGON
    features = [(feature.GetGeometryRef().GetArea(), feature) for feature in temp_layer]
    largest_polygon = max(features, key=lambda item: item[0])[1]

    # Fetch geometry of largest feature only
    largest_polygon_geom = largest_polygon.GetGeometryRef().Clone()

    # Create final shapefile with only the largest polygon
    final_layername = "POLYGONIZED_MASK"
    final_ds = driver.CreateDataSource(final_layername + ".shp")
    final_layer = final_ds.CreateLayer(final_layername, srs=spatial_ref, geom_type=ogr.wkbPolygon)

    # Add only the largest polygon
    feature_defn = final_layer.GetLayerDefn()
    out_feature = ogr.Feature(feature_defn)
    out_feature.SetGeometry(largest_polygon_geom)
    final_layer.CreateFeature(out_feature)

    # Cleanup
    temp_ds.Destroy()
    final_ds.Destroy()
```

**Key Issue:** This approach **discards all polygons except the largest one**. If the jurisdiction contains legitimate islands, disconnected territories, or areas separated by exclusion zones, they are completely removed from the analysis.

#### TerraCover Implementation

**File:** `evaluation.py` (lines 95-121)

```python
def create_mask_polygon(self, mask):
    '''
    Create municipality mask polygon
    :param mask: mask of the jurisdiction (binary map)
    '''
    in_ds = gdal.Open(mask)
    in_band = in_ds.GetRasterBand(1)

    # Set up spatial reference
    projection = in_ds.GetProjection().encode('utf-8', 'backslashreplace').decode('utf-8')
    spatial_ref = osr.SpatialReference()
    spatial_ref.ImportFromWkt(projection)

    # Create shapefile to store ALL polygons (no filtering)
    temp_layername = "POLYGONIZED_MASK"
    driver = ogr.GetDriverByName("ESRI Shapefile")
    temp_ds = driver.CreateDataSource(temp_layername + ".shp")
    temp_layer = temp_ds.CreateLayer(temp_layername, srs=spatial_ref)
    gdal.Polygonize(in_band, in_band, temp_layer, -1, [], callback=None)

    # Close datasets - ALL polygons are retained
    temp_layer = None
    temp_ds = None
    in_band = None
    in_ds = None
```

**Key Improvement:** TerraCover retains **all polygons** from the mask. The filtering logic is moved to a later stage where the dual-mask system can properly handle different geometries for grid generation vs. statistics calculation.

---

### 2. Thiessen Polygon Generation

#### UDef-ARP Implementation

**File:** `model_evaluation.py` (lines 348-403)

```python
def create_thiessen_polygon(self, grid_area, mask, density, deforestation, out_fn, raster_fn):
    '''
    Create thiessen polygon
    :param grid_area: assessment grid cell area or 100,000 (ha)
    :param mask: mask of the jurisdiction (binary map)  # SINGLE MASK
    ...
    '''
    # Open the Polygonized_Mask shapefile (contains only largest polygon)
    mask_df = gpd.GeoDataFrame.from_file('POLYGONIZED_MASK.shp')

    # Calculate grid size
    in_ds = gdal.Open(mask)
    grid_size = int(np.sqrt(grid_area * 10000)) // int(in_ds.GetGeoTransform()[1])

    # Systematic Sampling
    sample_points = []
    for y in range(-1 * grid_size, in_ds.RasterYSize + 1 * grid_size, grid_size):
        for x in range(-1 * grid_size, in_ds.RasterXSize + 1 * grid_size, grid_size):
            geo_x = in_ds.GetGeoTransform()[0] + x * in_ds.GetGeoTransform()[1]
            geo_y = in_ds.GetGeoTransform()[3] + y * in_ds.GetGeoTransform()[5]
            sample_points.append((geo_x, geo_y))

    # Create Voronoi
    coords = np.array(points_df['coords'].tolist())
    polygon = mask_df.geometry.unary_union
    vor = Voronoi(points=coords)

    # ... polygonize lines ...

    # Convert to GeoDataFrame
    polydf = gpd.GeoDataFrame(geometry=[polygon], crs=mask_df.crs)

    # Filter using SINGLE mask (same mask used for generation and filtering)
    thiessen_gdf = self.remove_edge_cells(voronois, polydf, 0.999)
```

**Method Signature:** `create_thiessen_polygon(self, grid_area, mask, density, deforestation, out_fn, raster_fn)`

Note: Uses **single `mask` parameter** for both Voronoi generation and edge filtering.

#### TerraCover Implementation

**File:** `evaluation.py` (lines 272-537)

```python
def create_thiessen_polygon(self, grid_area, mask_voronoi, mask_exclusions, density, deforestation, out_fn, raster_fn):
    '''
    Create thiessen polygon with improved methodology for handling exclusions.

    IMPORTANT: This method uses a two-mask approach to properly handle exclusions:
    1. mask_voronoi: Full jurisdictional area (jnr_value only, no exclusions) used to generate
       complete Voronoi polygons without fragmentation
    2. mask_exclusions: JNR area with exclusions applied (jnr_with_exclusions_mask) used to
       calculate final statistics after filtering

    This ensures that:
    - Voronoi polygons are generated over a continuous area (not fragmented by exclusions)
    - The 0.999 threshold filter works correctly to remove only edge polygons
    - Exclusions are applied AFTER filtering, affecting only final statistics

    :param grid_area: assessment grid cell area in hectares
    :param mask_voronoi: Full jurisdictional mask for Voronoi generation (no exclusions)
    :param mask_exclusions: Jurisdictional mask with exclusions for final statistics
    ...
    '''
    ## Polygonize VORONOI mask (full jurisdictional area, no exclusions)
    print("Polygonizing Voronoi mask...")
    self.create_mask_polygon(mask_voronoi)
    mask_voronoi_df = gpd.GeoDataFrame.from_file('POLYGONIZED_MASK.shp')

    ## Polygonize EXCLUSIONS mask (with exclusions applied)
    print("Polygonizing exclusions mask...")
    self.create_mask_polygon(mask_exclusions)
    mask_exclusions_df = gpd.GeoDataFrame.from_file('POLYGONIZED_MASK.shp')

    # Get raster dimensions from Voronoi mask
    in_ds = gdal.Open(mask_voronoi)
    pixel_size = int(in_ds.GetGeoTransform()[1])
    # ... grid calculations ...

    # Generate Voronoi tessellation
    vor = Voronoi(points=coords)
    # ... polygonize lines ...

    ## CRITICAL: Filter edge polygons using Voronoi mask (NO exclusions)
    print("Filtering edge polygons (99.9% threshold)...")
    clipped_gdf = self.remove_edge_cells(voronois, mask_voronoi_df, 0.999)
    print(f"Retained {len(clipped_gdf)} polygons after edge filtering")

    ## THEN: Apply exclusions mask to filtered polygons
    if len(clipped_gdf) > 0:
        print("Applying exclusions to grid...")

        # Assign original polygon IDs BEFORE applying exclusions
        clipped_gdf = clipped_gdf.copy()
        clipped_gdf['_voronoi_id'] = range(1, len(clipped_gdf) + 1)

        # Overlay filtered polygons with exclusions mask
        thiessen_with_exclusions = gpd.overlay(clipped_gdf, mask_exclusions_df,
                                                how="intersection", keep_geom_type=False)

        # Extract valid geometries and preserve Voronoi IDs
        # ... geometry extraction code ...

        # Dissolve fragments back to original Voronoi polygon IDs
        clipped_gdf = clipped_gdf.dissolve(by='_voronoi_id').reset_index()
```

**Method Signature:** `create_thiessen_polygon(self, grid_area, mask_voronoi, mask_exclusions, density, deforestation, out_fn, raster_fn)`

Note: Uses **two separate mask parameters**:
- `mask_voronoi`: For grid generation and edge filtering (continuous geometry)
- `mask_exclusions`: For final statistics calculation (with exclusions)

---

### 3. Edge Cell Filtering

#### UDef-ARP Implementation

**File:** `model_evaluation.py` (lines 326-346)

```python
def remove_edge_cells(self, full_voronoi_grid: GeoDataFrame, area_mask: GeoDataFrame,
                      area_percentile_threshold: float) -> GeoDataFrame:
    '''
    Ensure thiessen polygon cells retain percentile threshold of maximum size
    after intersection with mask of the jurisdiction
    '''
    thiessen_gdf = gpd.overlay(full_voronoi_grid, area_mask, how="intersection")

    # Get area of each polygon
    thiessen_gdf["area"] = thiessen_gdf.area

    max_area = thiessen_gdf["area"].max()

    # Calculate size of cell compared to max
    thiessen_gdf["percentcell"] = thiessen_gdf["area"] / max_area

    # Select cells with more than thresh% of their area
    thiessen_gdf = thiessen_gdf[thiessen_gdf["percentcell"] > area_percentile_threshold]

    return thiessen_gdf
```

#### TerraCover Implementation

**File:** `evaluation.py` (lines 246-270)

```python
def remove_edge_cells(self, full_voronoi_grid: GeoDataFrame, area_mask: GeoDataFrame,
                      area_percentile_threshold: float) -> GeoDataFrame:
    '''
    Ensure thiessen polygon cells retain percentile threshold of maximum size
    after intersection with mask of the jurisdiction
    '''
    # Use keep_geom_type=False to prevent warnings about dropped geometries
    thiessen_gdf = gpd.overlay(full_voronoi_grid, area_mask, how="intersection", keep_geom_type=False)

    # Filter to keep only Polygon and MultiPolygon geometries
    thiessen_gdf = thiessen_gdf[thiessen_gdf.geometry.type.isin(['Polygon', 'MultiPolygon'])]

    # Get area of each polygon
    thiessen_gdf["area"] = thiessen_gdf.area

    # Calculate size of cell compared to max
    thiessen_gdf["percentcell"] = thiessen_gdf["area"] / thiessen_gdf["area"].max()

    # Select cells with more than thresh% of their area
    thiessen_gdf = thiessen_gdf[thiessen_gdf["percentcell"] > area_percentile_threshold]

    return thiessen_gdf
```

**Key Improvements:**
1. Added `keep_geom_type=False` parameter to prevent geometry warnings
2. Added explicit filtering for Polygon/MultiPolygon geometries
3. Removed redundant variable assignment

---

### 4. Exclusion Handling

#### UDef-ARP Approach

UDef-ARP does **not have a dedicated mechanism** for handling exclusions separately from the main jurisdictional mask. Exclusions must be pre-applied to the input mask, which causes:

1. Fragmented mask geometry
2. Reduced maximum polygon area (due to fragmentation)
3. Edge cells that should be filtered may pass the 99.9% threshold
4. Inconsistent sample counts

#### TerraCover Approach

TerraCover introduces a sophisticated exclusion handling workflow:

**File:** `evaluation.py` (lines 363-403)

```python
## Apply exclusions mask to filtered polygons
if len(clipped_gdf) > 0:
    print("Applying exclusions to grid...")

    # Assign original polygon IDs BEFORE applying exclusions overlay
    # This preserves the identity of each Voronoi cell so that fragments
    # (islands) created by exclusion removal can be dissolved back together
    clipped_gdf = clipped_gdf.copy()
    clipped_gdf['_voronoi_id'] = range(1, len(clipped_gdf) + 1)

    # Overlay filtered polygons with exclusions mask to remove excluded areas
    thiessen_with_exclusions = gpd.overlay(clipped_gdf, mask_exclusions_df,
                                            how="intersection", keep_geom_type=False)

    # Extract polygons and multipolygons from GeometryCollections
    extracted_geoms = thiessen_with_exclusions['geometry'].apply(
        lambda geom: [g for g in geom.geoms if
                      g.geom_type in ['Polygon', 'MultiPolygon']] if geom.geom_type == 'GeometryCollection' else [
            geom]
    )

    # Explode while preserving the original index to maintain _voronoi_id mapping
    extracted_series = extracted_geoms.explode()
    clipped_gdf = gpd.GeoDataFrame({
        'geometry': extracted_series.values,
        '_voronoi_id': thiessen_with_exclusions.loc[extracted_series.index, '_voronoi_id'].values
    }, crs=thiessen_with_exclusions.crs)

    # Filter out non-polygon geometries
    polygon_mask = clipped_gdf['geometry'].apply(lambda geom: geom.geom_type in ['Polygon', 'MultiPolygon'])
    clipped_gdf = clipped_gdf[polygon_mask].copy()

    # Dissolve fragments back to their original Voronoi polygon IDs
    # This merges islands created by exclusion removal back into a single
    # MultiPolygon per original Voronoi cell, preserving the correct polygon count
    clipped_gdf = clipped_gdf.dissolve(by='_voronoi_id').reset_index()
```

**Key Features:**
1. **Voronoi ID Preservation:** Each polygon receives a unique ID before exclusions are applied
2. **Fragment Dissolution:** Fragments created by exclusion removal are merged back to their original Voronoi cell
3. **Geometry Type Filtering:** Handles GeometryCollections and filters out invalid geometries
4. **Correct Polygon Count:** The final count represents actual Voronoi cells, not fragments

---

## Impact on Sample Count

### Why Sample Counts Differ

For a 50,000 ha grid evaluation:
- **UDef-ARP with exclusions applied to mask:** ~92 samples
- **TerraCover with dual-mask approach:** ~60 samples

The difference is explained by the **99.9% threshold calculation**:

| Scenario | Maximum Polygon Area | 99.9% Threshold | Edge Cells Filtered |
|----------|---------------------|-----------------|---------------------|
| UDef-ARP (fragmented mask) | Smaller (due to exclusions) | Lower | Fewer cells filtered out |
| TerraCover (continuous mask) | Larger (full jurisdiction) | Higher | More cells filtered out |

### Visual Explanation

```
UDef-ARP (Single Fragmented Mask):
┌─────────────────────────────────┐
│  ████   ████   ████   ████      │  ← Fragments pass 99.9% threshold
│  ████   ████   ████   ████      │    (threshold is relative to
│       [EXCLUSION]               │     fragmented max area)
│  ████   ████   ████   ████      │
│  ████   ████   ████   ████      │
└─────────────────────────────────┘
Result: More samples (fragments counted)

TerraCover (Dual Mask - Voronoi Generation):
┌─────────────────────────────────┐
│  ████████████████████████████   │  ← Continuous geometry
│  ████████████████████████████   │    (threshold based on
│  ████████████████████████████   │     full cell area)
│  ████████████████████████████   │
│  ████████████████████████████   │
└─────────────────────────────────┘
Result: Fewer, more representative samples

TerraCover (Exclusion Application - After Filtering):
┌─────────────────────────────────┐
│  ████   ████   ████   ████      │  ← Exclusions applied AFTER
│  ████   ████   ████   ████      │    edge filtering, fragments
│       [EXCLUSION]               │    dissolved back to cells
│  ████   ████   ████   ████      │
│  ████   ████   ████   ████      │
└─────────────────────────────────┘
Result: Same cell count, proper exclusion handling
```

---

## Statistical Implications

### Sample Quality vs. Quantity

While TerraCover produces fewer samples, these samples are **more statistically robust**:

| Metric | UDef-ARP | TerraCover |
|--------|----------|------------|
| Sample Count | Higher | Lower |
| Sample Representativeness | Variable | Consistent |
| Edge Bias | Present | Minimized |
| Spatial Coverage | Fragmented | Uniform |
| Statistical Validity | Potentially inflated | Robust |

### Methodological Correctness

The VT7 methodology specifies that evaluation should use a systematic grid covering the jurisdictional area. TerraCover's approach ensures:

1. **Uniform Grid Generation:** Voronoi cells are generated over the complete jurisdiction without artificial fragmentation
2. **Consistent Threshold Application:** The 99.9% filter operates on true cell areas, not fragments
3. **Proper Exclusion Handling:** Excluded areas affect statistics calculation, not grid generation
4. **Preserved Cell Identity:** Each evaluation unit represents a single Voronoi cell, even if split by exclusions

---

## Additional Enhancements

Beyond the dual-mask system, TerraCover includes several additional improvements:

### 1. Voronoi Mask Generation Helper

**File:** `evaluation.py` (lines 821-873)

```python
def create_voronoi_mask(self, jnr_lb_full_areas, jnr_value, output_path):
    """
    Create a binary Voronoi mask containing only the analysis area (no exclusions).

    This mask is used for generating complete Voronoi polygons without fragmentation
    from exclusion zones.
    """
    # Open the JNR/LB full areas raster
    ds = gdal.Open(jnr_lb_full_areas)
    band = ds.GetRasterBand(1)
    data = band.ReadAsArray()

    # Create mask: 1 where jnr_value, 0 elsewhere
    voronoi_mask_data = np.where(data == jnr_value, 1, 0).astype(np.uint8)

    # Create output raster
    driver = gdal.GetDriverByName('GTiff')
    out_ds = driver.Create(output_path, ds.RasterXSize, ds.RasterYSize, 1, gdal.GDT_Byte)
    # ... save raster ...
```

### 2. Enhanced Plot Generation

**File:** `evaluation.py` (lines 565-792)

- Added Theil-Sen regression line in addition to OLS
- Improved error handling for insufficient data points
- Added statistics export to text file
- Enhanced axis scaling and formatting

### 3. Excel Output with Formatting

**File:** `evaluation.py` (lines 474-501)

```python
# Create Excel writer with openpyxl engine for formatting
with pd.ExcelWriter(excel_file_path, engine='openpyxl') as writer:
    export_df.to_excel(writer, sheet_name='Evaluation Grid', index=False)

    # Get workbook and worksheet objects
    workbook = writer.book
    worksheet = writer.sheets['Evaluation Grid']

    # Apply number format with 2 decimals and thousands separator
    for row in worksheet.iter_rows(min_row=2, min_col=2, max_col=4):
        for cell in row:
            cell.number_format = '#,##0.00'
```

### 4. Improved Temporary File Handling

TerraCover uses Python's `tempfile` module for all intermediate files, ensuring proper cleanup and avoiding conflicts with existing files in the working directory.

### 5. Comprehensive Progress Logging

Detailed console output shows each step of the evaluation process:

```
============================================================
Creating Thiessen Polygon Grid
============================================================
Grid area: 50,000 ha (500 km²)
Polygonizing Voronoi mask...
Polygonizing exclusions mask...
Grid cell size: 2236 pixels
Generating Voronoi tessellation from 1,024 sample points...
Generated 961 Voronoi polygons
Filtering edge polygons (99.9% threshold)...
Retained 60 polygons after edge filtering
Applying exclusions to grid...
Final grid: 60 polygons
Calculating zonal statistics...
```

---

## Conclusion

TerraCover's model evaluation module represents a significant methodological improvement over the original UDef-ARP implementation. The dual-mask system ensures:

1. **Correct Grid Generation:** Voronoi polygons are generated over continuous geometry, avoiding fragmentation artifacts
2. **Proper Edge Filtering:** The 99.9% threshold operates on true cell areas
3. **Accurate Exclusion Handling:** Exclusions affect only the final statistics, not the grid structure
4. **Statistical Robustness:** Fewer but more representative samples lead to more reliable model evaluation

While the sample count may be lower than the original implementation, the samples are **methodologically correct** and provide a more accurate assessment of model performance according to VT7 requirements.

---

## References

- Verra VT0007 Tool: Unplanned Deforestation Allocation and Risk Mapping Procedure
- Original UDef-ARP Implementation: https://github.com/Verra
- TerraCover Implementation: `terracover/modules/vt7/evaluation.py`

---

## Status in UDef-ARP v2.11

v2.11 adopted several of the surface-level evaluation changes but **not** the core architectural improvement (the dual-mask system).

| Improvement | v2.11 status | Evidence (`UDef-ARP-main 2.11/model_evaluation.py`) |
|-------------|--------------|------------------------------------------------------|
| Dual-mask system (separate grid vs. statistics masks) | **NOT IMPLEMENTED** | `create_thiessen_polygon` still takes a single `mask` parameter; no `mask_voronoi`/`mask_exclusions` |
| Keep all mask polygons (vs. largest only) | IMPLEMENTED | removes the largest-polygon filter; `create_mask_polygon` returns right after `gdal.Polygonize` (lines ~160–166) |
| Remove redundant `unary_union` | IMPLEMENTED | passes `mask_df` directly to `remove_edge_cells` (lines ~390–393) |
| `remove_edge_cells` hardening (`keep_geom_type=False`, geometry-type filter) | **NOT IMPLEMENTED** | function is identical to the Original (lines ~321–341) |
| Theil-Sen regression + improved scatter plot | IMPLEMENTED | Theil-Sen lines ~562–574; extended-range scatter lines ~497–556 |

**Verdict:** v2.11 picks up the cosmetic/statistical changes (Theil-Sen, scatter rendering) and the "keep all polygons" change, but **not** the dual-mask system or the `remove_edge_cells` hardening — the parts that actually make the evaluation methodologically robust.

### Reconciling an apparent contradiction between the TerraCover documents

Two TerraCover documents describe "keeping all mask polygons" with *opposite* value judgments, which can look contradictory at first:

- **This document** presents *keeping all polygons* as the **improvement** (see "Mask Polygon Creation" above): the Original discards every polygon except the largest, which silently deletes legitimate islands, disconnected territories, and areas separated by exclusion zones.
- **`VT7_UDef-ARP_Version_Comparison_2.11_vs_Original.md` (Section 9.7)** calls v2.11's *keeping all polygons* a **regression**: small fragments can survive into Voronoi generation and slip through the 99.9% edge filter as noisy geometry.

**These two statements are not actually in conflict.** The value of "keep all polygons" depends entirely on *what machinery surrounds it*:

1. **"Keep all polygons" is necessary but not sufficient.** Retaining every polygon is only the first building block. In isolation it is neutral-to-risky: it preserves legitimate islands, but it also preserves noise fragments. Whether that is good or bad is decided by the *next* steps, not by this line.

2. **TerraCover makes it safe with the dual-mask machinery.** In TerraCover, the Voronoi grid is generated and edge-filtered against `mask_voronoi` — the *full, continuous* jurisdiction with **no** exclusions — and exclusions/fragments are applied only *after* filtering, then dissolved back to their original Voronoi-cell IDs (`_voronoi_id`). In that pipeline, keeping all polygons cannot corrupt grid generation, because the grid never sees the fragmented or excluded geometry. The 99.9% threshold is computed against the true, continuous cell area.

3. **v2.11 kept the building block but not the machinery.** v2.11 still uses a **single mask** for both Voronoi generation and edge filtering, has **no** exclusion-after-filter / fragment-dissolution step, and did **not** add the `keep_geom_type=False` / geometry-type hardening to `remove_edge_cells`. So it removed the Original's one safeguard (collapsing to a single clean polygon) *without* installing a replacement — inheriting the **downside** of "keep all" (noise fragments passing the edge filter, unstable sample counts) with **none** of the upside.

In one sentence: **the exact same "keep all polygons" change is an improvement inside TerraCover's dual-mask context and a regression inside v2.11's single-mask context.** Polygon retention must be judged together with the surrounding grid/exclusion architecture, never in isolation:

| Version | Polygon handling | Net effect |
|---------|------------------|------------|
| **Original** | Largest polygon only | Crude safeguard: keeps the single-mask pipeline clean, but silently drops legitimate disconnected areas (islands, split territories). |
| **v2.11** | Keep all, under a **single** mask | Drops the safeguard and adds no replacement → the Section 9.7 regression (fragment noise through the 99.9% filter). |
| **TerraCover** | Keep all, under the **dual-mask** + exclusion-after-filter + fragment-dissolution pipeline | Correct: the only version that both preserves legitimate geometry *and* controls fragment noise. |

*Documentation note:* to prevent future confusion, Section 9.7 of the Version-Comparison document could add a one-line pointer clarifying that "keep all polygons" is only a regression **in the absence of** the dual-mask system, cross-referencing this section.

---

*Document Version: 1.0*
*Last Updated: February 2026*
*Author: Terra Global Capital*
