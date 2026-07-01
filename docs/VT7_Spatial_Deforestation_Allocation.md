# VT0007 Spatial Deforestation Allocation Module

## Overview

The `udef_arp_spatial_deforestation.py` module implements a spatial allocation algorithm that combines VT0007 deforestation density maps with TerraChange Empirical Transition Potential (ETP) to determine which specific pixels will be deforested during the Validity Period.

This approach bridges two complementary methodologies:
- **VT0007**: Determines **HOW MUCH** deforestation will occur (methodology-compliant quantification)
- **TerraChange ETP**: Determines **WHERE** deforestation will occur (empirically-driven spatial allocation)

## Key Design Decisions

- **Stratification**: Area × Region (all forest classes compete together within each stratum)
- **Targets calculated BEFORE filtering**: Ensures total deforestation matches density map values
- **Deficit redistribution**: If a region has deficit, redistributes to other regions within the same Area

## Use Case

This module is used when:
1. VT0007 is used for deforestation modeling (compliant with VM0048 methodology)
2. TerraChange is used for degradation modeling
3. TerraChange needs to know where deforestation occurred to model subsequent degradation
4. The modified LULC output serves as input to TerraChange for degradation-only modeling
5. Multiple areas with separate TerraChange runs need to be processed together

## Process Flow

The algorithm follows a three-step process:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         STEP 1: QUANTIFICATION                          │
│                    (Targets calculated BEFORE filtering)                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   VT0007 Density Map (ha/pixel/year)                                   │
│            │                                                            │
│            ▼                                                            │
│   Overlay with Modeling Regions + Area Mask (if provided)              │
│            │                                                            │
│            ▼                                                            │
│   For each STRATUM (Area × Region):                                    │
│      • Sum ALL density values within stratum                           │
│      • Multiply by Validity Period years                               │
│      • Convert hectares to pixel count                                 │
│            │                                                            │
│            ▼                                                            │
│   Output: Target pixels per stratum                                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    STEP 2: STRATUM FILTERING (Optional)                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   If stratum_filter_kernel is specified:                               │
│            │                                                            │
│            ▼                                                            │
│   Create stratum map: area × 100000 + region × 100 + 1 (forest)       │
│   (Non-forest pixels = 0)                                              │
│            │                                                            │
│            ▼                                                            │
│   For each unique stratum:                                             │
│      • Apply morphological opening (erosion + dilation)                │
│      • Remove isolated pixels that don't survive                       │
│            │                                                            │
│            ▼                                                            │
│   Update eligible forest mask (filtered pixels are excluded)           │
│   Note: This does NOT reduce the targets calculated in Step 1          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│            STEP 3: SPATIAL ALLOCATION WITH DEFICIT REDISTRIBUTION       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   FIRST PASS: Per-stratum allocation                                   │
│   For each STRATUM (Area × Region):                                    │
│      • Filter eligible forest pixels belonging to this stratum         │
│      • Rank pixels by ETP value (descending)                           │
│      • Select top N pixels (N = target from Step 1)                    │
│      • Track deficit if insufficient pixels available                  │
│            │                                                            │
│            ▼                                                            │
│   SECOND PASS: Deficit redistribution within same Area                 │
│   For each AREA with deficit:                                          │
│      • Find all remaining eligible pixels in this Area                 │
│      • Rank by ETP (descending)                                        │
│      • Select additional pixels to cover area's total deficit          │
│            │                                                            │
│            ▼                                                            │
│   Mark all selected pixels as deforestation (value = 1)                │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              OUTPUTS                                    │
├─────────────────────────────────────────────────────────────────────────┤
│   • Deforestation Mask (binary: 1=deforestation, 0=no change)          │
│   • Modified LULC (forest pixels → non-forest where deforested)        │
│   • Allocation Report Excel (per-stratum statistics + log)             │
└─────────────────────────────────────────────────────────────────────────┘
```

## Step 1: Quantification (Target Calculation)

### Purpose
Calculate how many hectares (and pixels) should be deforested in each stratum during the Validity Period. This is done **BEFORE** any filtering to ensure the total deforestation matches the density map values.

### Implementation

The `_calculate_stratum_targets()` method performs this step:

```python
for area_id in unique_areas:  # If area_mask provided
    for region_id in unique_regions:
        # Create mask for this stratum (Area × Region)
        # NO LULC filtering - sum ALL density values
        stratum_mask = (
            (regions_array == region_id) &
            (density_array != nodata_density) &
            (~np.isnan(density_array))
        )

        # Add area constraint if area_mask provided
        if area_array is not None:
            stratum_mask = stratum_mask & (area_array == area_id)

        # Sum density values (ha/pixel/year)
        density_sum = np.sum(density_array[stratum_mask])

        # Calculate total hectares for validity period
        target_hectares = density_sum * validity_period_years

        # Convert to pixels
        target_pixels = ceil(target_hectares / pixel_area_ha)
```

### Key Formula

```
target_hectares = Σ(density_values) × validity_period_years
target_pixels = ⌈target_hectares / pixel_area_ha⌉
```

Where:
- `density_values`: VT0007 density map values within the stratum (ha/pixel/year)
- `validity_period_years`: Length of the Validity Period (e.g., 10 years)
- `pixel_area_ha`: Area of each pixel in hectares

### Example

| Area | Region | Sum of Density | VP Years | Target (ha) | Target Pixels |
|------|--------|----------------|----------|-------------|---------------|
| 1 | R1 | 50 ha/year | 10 | 500 ha | 5,625 |
| 1 | R2 | 25 ha/year | 10 | 250 ha | 2,813 |
| 2 | R1 | 100 ha/year | 10 | 1,000 ha | 11,249 |

## Step 2: Stratum Filtering (Optional)

### Purpose
Remove isolated forest pixels from each stratum before allocation to reduce salt-and-pepper effect caused by fragmented strata at boundaries between modeling regions.

### Key Guarantee
**Targets are NOT recalculated after filtering.** This ensures that the total deforestation allocated equals the density map values, even if some pixels are filtered out. The filtered pixels simply cannot participate in the allocation, which may cause deficit that is redistributed within the same Area.

### Implementation

When `stratum_filter_kernel` is specified (e.g., 3, 5, 7):

```python
# Create combined stratum map (only forest pixels)
# Groups by: Area × Region × forest (binary)
stratum_map[valid_forest] = area * 100000 + region * 100 + 1
stratum_map[non_forest_pixels] = 0

# For each unique stratum, apply morphological opening
for stratum_value in unique_strata:
    stratum_mask = (stratum_map == stratum_value)
    opened_mask = binary_opening(stratum_mask, iterations=kernel_size//2)
    removed_pixels = stratum_mask & ~opened_mask
    # Mark removed pixels as ineligible

# Update eligible_mask: only surviving pixels can be allocated
eligible_mask = (filtered_stratum_map > 0)
```

### Key Guarantees
- **Only removes pixels**: Never converts non-forest to forest
- **Does not reduce targets**: Targets are calculated before filtering
- **Per-stratum filtering**: Each stratum (Area × Region × forest) is filtered independently

## Step 3: Spatial Allocation with Deficit Redistribution

### Purpose
Select which specific pixels will be deforested based on their transition probability (ETP), with deficit redistribution to maintain VT0007 compliance.

### Implementation

The `_allocate_deforestation_pixels()` method performs this step in two passes:

**First Pass: Per-stratum allocation**

```python
for target in targets:
    # Create mask for this stratum (Area × Region × eligible forest)
    stratum_mask = (
        (regions_array == target.region_id) &
        eligible_mask &  # Only eligible forest pixels
        (etp_array != nodata_etp) &
        (~np.isnan(etp_array)) &
        (etp_array > 0) &
        (deforestation_mask == 0)  # Not already allocated
    )

    # Add area constraint if applicable
    if target.area_id is not None:
        stratum_mask = stratum_mask & (area_array == target.area_id)

    # Sort by ETP (descending) and select top N pixels
    n_to_select = min(target.target_pixels, len(stratum_etp_values))
    # ... select and mark pixels

    # Track deficit
    target.deficit_hectares = max(0, target.target_hectares - target.allocated_hectares)
```

**Second Pass: Deficit redistribution within same Area**

```python
for area_id, area_targets in targets_by_area.items():
    total_deficit_ha = sum(t.deficit_hectares for t in area_targets)
    total_deficit_pixels = ceil(total_deficit_ha / pixel_area_ha)

    if total_deficit_pixels == 0:
        continue

    # Find all eligible pixels in this area not yet allocated
    area_mask = (
        eligible_mask &
        (etp_array > 0) &
        (deforestation_mask == 0)
    )
    if area_id is not None:
        area_mask = area_mask & (area_array == area_id)

    # Select top N pixels by ETP to cover deficit
    n_to_select = min(total_deficit_pixels, len(area_etp_values))
    # ... select and mark additional pixels
```

### Key Concept: Deficit Redistribution

When a region within an Area has deficit (fewer eligible pixels than the target), the deficit is redistributed to other regions within the **same Area**. This ensures:

1. Total deforestation per Area matches the density map
2. Deforestation stays within the correct Area (important for multi-area projects)
3. Pixels with highest ETP across the entire Area are selected

## Input Requirements

| Input | Description | Units | Required |
|-------|-------------|-------|----------|
| `density_map` | VT0007 deforestation density | ha/pixel/year | Yes |
| `etp_map` | TerraChange ETP for deforestation | Probability (0-1 or 0-10000) | No (optional) |
| `lulc_map` | Land use/land cover classification | Integer classes | Yes |
| `modeling_regions` | Administrative/modeling regions | Integer IDs | Yes |
| `area_mask` | Area zones for multi-area projects | Integer IDs | No |

**Important**:
- All input rasters must be spatially aligned (same extent, resolution, CRS).
- If `etp_map` is not provided, density values are used as ranking criteria (pixels with higher density are selected first).

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `validity_period_years` | Length of the Validity Period | 10 |
| `class_def_file` | Excel file with forest class definitions | None |
| `forest_classes` | List of forest class IDs | None |
| `non_forest_class` | Class value for deforested pixels | 0 |
| `stratum_filter_kernel` | Kernel size for filtering isolated pixels (3, 5, 7, etc.) | None |

## Output Files

| Output | Description | Data Type |
|--------|-------------|-----------|
| `[output_file]` | Deforestation mask | UInt8 (1=deforestation, 0=no change) |
| `[output_file]_modified_lulc.tif` | Modified LULC with deforested pixels as non-forest | Same as input LULC |
| `[output_file]_allocation_report.xlsx` | Excel report with allocation details | Excel (2 sheets) |

### Excel Report Structure

**Sheet "Stratum Details"**: Per-stratum allocation table
| Area | Region | Target (ha) | Target Pixels | Available | Allocated Pixels | Allocated (ha) | Deficit (ha) |
|------|--------|-------------|---------------|-----------|------------------|----------------|--------------|

**Sheet "Log"**: Summary statistics, input files, and output files

## Usage Examples

### Basic Usage with ETP (Single Area)

```python
from terracover.modules.udef_arp_spatial_deforestation import udef_arp_spatial_deforestation

success = udef_arp_spatial_deforestation(
    density_map="vt7_adjusted_density_VP.tif",
    etp_map="terrachange_etp_deforestation.tif",
    lulc_map="lulc_baseline.tif",
    modeling_regions="modeling_regions.tif",
    output_file="deforestation_allocation.tif",
    validity_period_years=10,
    forest_classes=[5, 6, 7, 8],
    non_forest_class=0
)
```

### Without ETP (Uses Density for Ranking)

```python
success = udef_arp_spatial_deforestation(
    density_map="vt7_adjusted_density_VP.tif",
    lulc_map="lulc_baseline.tif",
    modeling_regions="modeling_regions.tif",
    output_file="deforestation_allocation.tif",
    validity_period_years=10,
    forest_classes=[5, 6, 7, 8]
    # No etp_map provided - uses density values as ranking
)
```

### Multi-Area Projects

```python
success = udef_arp_spatial_deforestation(
    density_map="combined_density.tif",
    etp_map="combined_etp.tif",
    lulc_map="lulc_baseline.tif",
    modeling_regions="combined_regions.tif",
    output_file="deforestation_allocation.tif",
    validity_period_years=10,
    forest_classes=[5, 6, 7, 8],
    area_mask="area_zones.tif"  # Prevents cross-area pixel competition
)
```

### With Stratum Filtering

```python
success = udef_arp_spatial_deforestation(
    density_map="vt7_density.tif",
    etp_map="terrachange_etp.tif",
    lulc_map="lulc.tif",
    modeling_regions="regions.tif",
    output_file="output.tif",
    forest_classes=[5, 6, 7, 8],
    stratum_filter_kernel=5  # Removes isolated forest pixels
)
```

## Integration with TerraChange

The modified LULC output can be used as input to TerraChange for degradation modeling:

```
VT0007 Density Map ──┐
                     │
TerraChange ETP ─────┼──► Spatial Allocation ──► Modified LULC
                     │                                  │
LULC Baseline ───────┘                                  │
                                                        ▼
                                              TerraChange Degradation
                                                    Modeling
```

This workflow ensures:
1. Deforestation quantities comply with VT0007 methodology
2. Spatial allocation uses empirical drivers from TerraChange
3. Degradation modeling knows exactly where forest was removed

## Handling Edge Cases

### Insufficient Pixels

If a stratum has fewer eligible pixels than the target:
- The algorithm allocates all available pixels in the first pass
- Deficit is tracked per stratum
- In the second pass, deficit is redistributed within the same Area
- If the entire Area has deficit, it is reported in the Excel report

### Zero ETP Values

Pixels with ETP ≤ 0 are excluded from allocation.

### NoData Handling

NoData values are excluded from both quantification and allocation.

### Isolated Pixels (Salt-and-Pepper Effect)

Use `stratum_filter_kernel` to remove isolated forest pixels before allocation:
- Caused by fragmentation at stratum boundaries
- Opening operation removes small fragments
- Only removes pixels, never adds
- Does NOT reduce targets (calculated before filtering)

## Technical Notes

1. **Memory Efficiency**: All rasters are loaded into memory simultaneously. For very large rasters, consider using chunked processing.

2. **Pixel Area Calculation**: Assumes projected CRS with units in meters. Pixel area is calculated as:
   ```python
   pixel_area_ha = (pixel_width * pixel_height) / 10000.0
   ```

3. **Rounding**: Target pixels use ceiling to ensure at least the target hectares are allocated:
   ```python
   target_pixels = int(np.ceil(target_hectares / pixel_area_ha))
   ```

4. **Deterministic Results**: Given the same inputs, the algorithm produces identical results (no random component).

5. **VT0007 Compliance**: The total allocated hectares should equal the sum of density values × validity period. Any difference is due to insufficient eligible pixels.

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025 | Initial implementation |
| 1.1 | 2025 | Added area_mask support for multi-area projects |
| 1.2 | 2025 | Added stratum_filter_kernel for isolated pixel removal |
| 1.3 | 2025 | Changed report format from text to Excel |
| 2.0 | 2025 | Major redesign: targets BEFORE filtering, Area × Region stratification, deficit redistribution |

---
*Document generated for TerraCover VT0007 Spatial Deforestation Allocation Module*
