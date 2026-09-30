# coding=utf-8
# ------------------------------------------------------------------------
#
#   Copyright:          © Terra Global Capital. All rights reserved.
#   Author:             david.montoya@terraglobalcapital.com
#   Python version:     3.11
#   GDAL version:       3.10.3
#   Year:               2025
#
#   This code is proprietary and confidential.
#   Unauthorized copying or distribution is prohibited.
#
# ------------------------------------------------------------------------

"""
VT7 output vocabulary (deforestation vs degradation).

VT0007 is written for unplanned DEFORESTATION, but the same procedure runs unchanged on the
degradation benchmark (FCBM-DG): the FCBM index means the same thing in both — 6/7 is the
T1-T2 loss and 8 the T2-T3 loss — only WHAT was lost differs (forest cover vs canopy). So the
`benchmark_type` flag this module serves is purely a matter of words: not one number, threshold
or class boundary changes with it.

Everything that has to say the word lives here, so a run labels its plots, tables, logs and
shapefile fields consistently instead of hard-coding "deforestation" in six files. The values
mirror `fcbm.py`'s own `benchmark_type` on purpose: the pair of modules is configured with one
vocabulary.
"""

from collections import namedtuple


# The two vocabularies, as accepted by the `benchmark_type` argument. Same strings as fcbm.py.
BENCHMARK_DF = "deforestation"
BENCHMARK_DG = "degradation"
BENCHMARK_TYPES = (BENCHMARK_DF, BENCHMARK_DG)

# noun:  sentence-case, for titles, labels and column names ("Actual Deforestation(ha)")
# lower: running prose and file names ("Frequency of deforestation (pixels)")
# abbr:  the 10-character shapefile field budget ("ActualDef" / "ActualDeg")
Terms = namedtuple("Terms", ["benchmark_type", "noun", "lower", "abbr"])

_TERMS = {
    BENCHMARK_DF: Terms(BENCHMARK_DF, "Deforestation", "deforestation", "Def"),
    BENCHMARK_DG: Terms(BENCHMARK_DG, "Degradation", "degradation", "Deg"),
}


def normalize_benchmark_type(benchmark_type):
    """Return the canonical benchmark type, or the raw value when it is not one of the two.

    Lenient on purpose, like fcbm._normalize_benchmark_type: validation reports the unknown
    value with a readable message, so this never raises on the way in.
    """
    value = str(benchmark_type).strip().lower() if benchmark_type is not None else ""
    return value if value in BENCHMARK_TYPES else (benchmark_type or BENCHMARK_DF)


def terms(benchmark_type=BENCHMARK_DF):
    """The words for the requested benchmark. Unknown values fall back to the deforestation set,
    so a bad flag mislabels nothing worse than the default (validation stops the run anyway)."""
    return _TERMS.get(normalize_benchmark_type(benchmark_type), _TERMS[BENCHMARK_DF])


# ------------------------------------------------------------------------
# Column and field names
# ------------------------------------------------------------------------
# These are contracts, not decoration: the frequency table is written in the fitting phase and
# read back by name in the prediction phase, and the evaluation grid columns are what the
# downstream workflows parse. Build them from one place so both ends always agree.

def frequency_columns(benchmark_type=BENCHMARK_DF):
    """(total, average) column names of the relative-frequency table."""
    noun = terms(benchmark_type).noun
    return f"Total {noun}(pixel)", f"Average {noun}(pixel)"


def evaluation_columns(benchmark_type=BENCHMARK_DF):
    """(actual, predicted) column names of the evaluation grid table."""
    noun = terms(benchmark_type).noun
    return f"Actual {noun}(ha)", f"Predicted {noun}(ha)"


def residual_fields(benchmark_type=BENCHMARK_DF):
    """(actual, predicted) field names of the residuals shapefile (10-character limit)."""
    abbr = terms(benchmark_type).abbr
    return f"Actual{abbr}", f"Pred{abbr}"


def align_frequency_columns(df, benchmark_type=BENCHMARK_DF):
    """Rename a frequency table read from disk into the vocabulary this run speaks.

    A CAL/HRP table written before this flag existed — or by a run of the other benchmark type —
    carries the other pair of column names, and the prediction phase indexes them by name. Left
    alone that raises a bare KeyError deep inside the density map; renaming here means an old
    fitting table still drives a new prediction run.

    Returns the same DataFrame (renamed in place is avoided: pandas returns a copy).
    """
    wanted_total, wanted_average = frequency_columns(benchmark_type)
    renames = {}
    for other in BENCHMARK_TYPES:
        other_total, other_average = frequency_columns(other)
        if other_total != wanted_total and other_total in df.columns:
            renames[other_total] = wanted_total
        if other_average != wanted_average and other_average in df.columns:
            renames[other_average] = wanted_average
    return df.rename(columns=renames) if renames else df
