# VT7 Evaluation: Raw-Hectare Statistics over an Intact Grid, and Additional Statistics

**Status:** current since 2026-11-09. Change 1 below replaces the residual normalisation this
document described from 2026-09-29, after Verra's answer on how the evaluation grid treats the
identified exclusions.

## Issue Summary

Two separate matters in the model evaluation of VT0007 §5.4, both in `create_plot`:

1. **How the identified exclusions enter the evaluation.** The Thiessen grid is generated over the
   jurisdiction, the incomplete edge cells are removed, and the exclusions are then cut out of the
   remaining cells — so a cell that holds an exclusion comes out smaller than the nominal grid area.
   From 2026-09-29 to 2026-11-09 observed and predicted were scaled up to the nominal grid area
   before MedAE and MAE were computed, and cells with no change on either side (both ≤ 0.01 ha) were
   dropped. Neither is done any more.

2. **The evaluation reported R², OLS, Theil-Sen and MedAE only.** UDef-ARP v2.14.1 reports several
   further statistics that were not available here.

## Location

- **File**: `terracover/modules/vt7/evaluation.py`
- **Function**: `create_plot`

## Change 1 — the grid is kept intact, and every statistic is on raw hectares

Verra's position (2026-11): keep the evaluation grid as consistent and intact as possible. The only
cells removed are the incomplete cells along the jurisdiction boundary that fail the area threshold;
no cell is split around an exclusion, and no otherwise valid cell is removed for holding one. An
exclusion legitimately considered to have no risk of unplanned deforestation contributes neither
predicted nor observed deforestation, so it adds nothing to the absolute error of the cell that holds
it.

MedAE depends on the size and geometry of the evaluation units. Splitting cells changes the units;
removing cells changes the set of errors the median is taken from; and scaling a trimmed cell up to
the nominal area lets the exclusion change that cell's error. So:

- Observed and predicted are the **raw hectares** of each cell. No scaling.
- **Every cell is a sample**, a cell with no change on either side included.
- MedAE, MAE, the OLS and Theil-Sen regressions, R², Agreement, Difference and IoU are all computed
  on those values — as UDef-ARP v2.14.1 (`model_evaluation.py::create_plot`) does.
- The percentage of MedAE and MAE is of the **nominal** grid area.

What was already in place and is unchanged: the edge filter (99.9 % of the largest cell) is applied
to the mask **without** exclusions, and the exclusions are cut out afterwards, each cell's fragments
dissolved back into one cell. The benchmark measures its distance to non-forest with the exclusions
as NoData, so they do not create forest edges around themselves.

### Effect

On a test jurisdiction of roughly 5.1 M ha with 46 assessment cells (79,090 ha grid), the cells span
58,962 – 78,703 ha. Against the normalised figures, MedAE in the calibration / confirmation periods:

| Model | Normalised (until 2026-11-09) | Raw hectares (now) |
|---|---|---|
| Benchmark | 616.76 / 445.02 ha | 596.55 / 439.96 ha |
| Alternative M1 | 480.09 / 394.28 ha | 466.90 / 368.04 ha |
| Alternative M2 | 578.49 / 587.87 ha | 550.45 / 570.37 ha |

Model qualification under VT0007 §5.4 — the alternative's MedAE below the benchmark's in both the
fitting and the prediction period — is the same in both: M1 qualifies, M2 does not. No cell of that
test had zero change on both sides.

## Change 2 — statistics added, to match UDef-ARP v2.14.1

- **MAE** — mean absolute error, alongside the median.
- **Agreement**, **Difference** — the shared and unshared portions of observed versus predicted.
- **IoU** — intersection over union.
- **Interactive HTML plot** (Plotly) whose hover names each cell and shows its area, its observed and
  predicted values, and its absolute error. The static PNG is still written; the HTML is additional.
  The Plotly import is optional — if the library is absent the PNG is produced as before and the run
  continues.
- Regression lines are drawn across the **full axis** rather than only over the range of the
  observed points, which is how v2.14.1 draws them.

## Note on the order of operations

A related question is whether the exclusions mask should be applied **before** testing each cell
against the 99.9 % edge-cell area criterion, rather than after. It is not, and deliberately so:
applied to geometry the exclusions have already trimmed, the criterion is satisfied only by interior
cells the exclusions happen not to touch. On the test jurisdiction above that reduced the assessment
from 46 cells to 3, and under 7 % of the area the evaluation is meant to cover — at which point the
regression is degenerate, R² is 1.000 by construction and Theil-Sen coincides with OLS. Verra's
answer of 2026-11 keeps the same order: only incomplete edge cells are removed.
