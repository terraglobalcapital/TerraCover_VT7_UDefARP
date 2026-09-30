# VT7 Evaluation: Residual Normalisation and Additional Statistics

## Issue Summary

Two separate matters in the model evaluation of VT0007 §5.4, both in `create_plot`:

1. **The assessment cells are not equal in area, and the statistics treated them as if they were.**
   The Thiessen grid is generated over the jurisdiction and then clipped by the exclusions mask, so
   cells at the boundary — and cells containing an excluded area — come out smaller than the nominal
   grid area. Because MedAE is the median of absolute differences **in hectares**, a smaller cell
   contributes a smaller residual for reasons that have nothing to do with how well the model fits.

2. **The evaluation reported R², OLS, Theil-Sen and MedAE only.** UDef-ARP v2.14.1 reports several
   further statistics that were not available here.

## Location

- **File**: `terracover/modules/vt7/evaluation.py`
- **Function**: `create_plot`

## Change 1 — residuals normalised to the nominal grid area

Observed and predicted hectares are scaled by `grid_area / cell_area` before any per-cell statistic
is computed:

```python
area_ha = np.array(clipped_gdf_filtered['Area_ha'], dtype=np.float64)
if np.any(area_ha <= 0):
    raise ValueError("create_plot: an assessment cell has zero or negative area; ...")
scale = float(grid_area) / area_ha
X_raw, Y_raw = X.copy(), Y.copy()
X = X * scale
Y = Y * scale
```

A cell that retains 75 % of the nominal area has its observed and predicted values scaled by 1.33,
which is what "what would this cell have shown at full size" means. The cells are then compared on
equal footing.

### Why the nominal grid area, and not the largest observed cell

`A_ref` is the **nominal** grid area — the value the run was configured with — rather than the
largest cell actually present. It is a constant of the method rather than a property of one sample,
so MedAE stays comparable between runs and between jurisdictions, and it matches the denominator
already used to express MedAE as a percentage. Taking the largest observed cell would make the
statistic depend on which cell happened to survive clipping.

### Which statistic uses which basis — deliberately split

| Statistic | Basis | Why |
|---|---|---|
| MedAE, MAE | normalised | they compare cells **to one another**, so the cells must be comparable |
| Agreement, Difference, IoU | raw hectares | they aggregate **over all cells** and keep a physical reading; normalising them would overweight the cells the exclusions trimmed |

MedAE and MAE are also reported on the raw basis, for traceability. The statistics file states the
basis of each figure in its own text, so a reader never has to infer it.

### Guard

A cell of zero or negative area raises rather than producing an infinite scale factor. That can only
arise from a malformed grid, and silently dividing by it would put `inf` into the median.

## Change 2 — statistics added, to match UDef-ARP v2.14.1

- **MAE** — mean absolute error, alongside the median.
- **Agreement**, **Difference** — the shared and unshared portions of observed versus predicted.
- **IoU** — intersection over union.
- **Interactive HTML plot** (Plotly) whose hover names each cell and shows its area, its normalised
  and raw values, and its absolute error. The static PNG is still written; the HTML is additional.
  The Plotly import is optional — if the library is absent the PNG is produced as before and the run
  continues.
- Regression lines are drawn across the **full axis** rather than only over the range of the
  observed points, which is how v2.14.1 draws them.

## Effect

Normalisation moves MedAE by a few per cent: on a test jurisdiction of roughly 5.1 M ha with 46
assessment cells, MedAE rose by 3.5 % in the calibration period and 1.4 % in the confirmation
period, with per-cell scaling factors between 1.005 and 1.341. The direction of the change is a
property of the sample, not of the method.

Model qualification under VT0007 §5.4 — the alternative's MedAE below the benchmark's in both the
fitting and the prediction period — was unaffected in that test.

## Note on the order of operations

A related question is whether the exclusions mask should be applied **before** testing each cell
against the 99.9 % edge-cell area criterion, rather than after. It is not, and deliberately so:
applied to geometry the exclusions have already trimmed, the criterion is satisfied only by interior
cells the exclusions happen not to touch. On the test jurisdiction above that reduced the assessment
from 46 cells to 3, and under 7 % of the area the evaluation is meant to cover — at which point the
regression is degenerate, R² is 1.000 by construction and Theil-Sen coincides with OLS.

Normalisation addresses the comparability of unequal cells directly, without discarding the sample.
