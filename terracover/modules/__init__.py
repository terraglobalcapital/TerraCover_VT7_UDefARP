# coding=utf-8
# ------------------------------------------------------------------------
#   
#   Copyright:          © Terra Global Capital. All rights reserved.
#   Author:             david.montoya@terraglobalcapital.com
#   Python version:     3.13
#   GDAL version:       3.10.3
#   GeoPandas version:  1.1.1
#   Year:               2025
#
#   This code is proprietary and confidential.
#   Unauthorized copying or distribution is prohibited.
# 
# ------------------------------------------------------------------------


# Lazy import mechanism - imports modules only when accessed
# This prevents circular imports and improves package load time
_LAZY_IMPORTS = {
    # Raster Processing
    "reproject": ("reproject", "reproject"),
    "raster_colors": ("raster_colors", "raster_colors"),
    "merge_rasters": ("merge_rasters", "merge_rasters"),
    "convert_raster": ("raster_convert", "convert_raster"),
    "rescale_raster": ("rescale", "rescale_raster"),
    "raster_align": ("raster_align", "raster_align"),
    "raster_stack": ("raster_stack", "raster_stack"),
    "ancillary_stack": ("ancillary", "ancillary_stack"),
    "raster_calculator": ("raster_calculator", "raster_calculator"),
    "clip_raster": ("clip_raster", "clip_raster"),

    # Raster Analysis
    "spectral_index": ("spectral_index", "spectral_index"),
    "euclidean_distance": ("euclidean_distance", "euclidean_distance"),
    "local_stats": ("local_stats", "local_stats"),
    "class_density": ("class_density", "class_density"),
    "speckle_filter": ("speckle_filter", "speckle_filter"),
    "reclassify": ("reclassify", "reclassify"),

    # Classification & Change Detection
    "raster_classification": ("raster_classification", "raster_classification"),
    "temporal_filter": ("temporal_filter", "temporal_filter"),
    "transitions": ("transitions", "transitions"),
    "change_map": ("change_map", "change_map"),
    "non_allowed_transitions": ("non_allowed_transitions", "non_allowed_transitions"),
    "probability_filter": ("probability_filter", "probability_filter"),
    "local_deforestation": ("local_deforestation", "local_deforestation"),

    # Vector Operations
    "rasterize": ("rasterize", "rasterize"),
    "vectorize": ("vectorize", "vectorize"),
    "raster_value_to_point": ("raster_value_to_point", "raster_value_to_point"),

    # Validation
    "accuracy_assessment": ("accuracy", "accuracy_assessment"),

    # VMD0055
    "fcbm": ("fcbm", "fcbm"),
    "exclusions": ("exclusions", "exclusions"),
    "leakage_belt": ("leakage_belt", "leakage_belt"),
    "jnr_regions": ("jnr_regions", "jnr_regions"),
    "activity_shifting_leakage": ("activity_shifting_leakage", "activity_shifting_leakage"),
    "udef_arp": ("udef_arp", "udef_arp"),

    # Advanced Tools
    "python_console": ("python_console", "python_console"),
}

def __getattr__(name):
    """
    Lazy import mechanism for module functions.

    This function is called when an attribute is accessed but hasn't been imported yet.
    It defers imports until they're actually needed, improving package load time and
    preventing circular import issues.

    Args:
        name: The name of the attribute being accessed

    Returns:
        The requested function from the module

    Raises:
        AttributeError: If the requested attribute doesn't exist
    """
    if name in _LAZY_IMPORTS:
        module_name, func_name = _LAZY_IMPORTS[name]
        from importlib import import_module
        module = import_module(f".{module_name}", package="terracover.modules")
        func = getattr(module, func_name)
        # Cache the imported function in the module's namespace
        globals()[name] = func
        return func
    raise AttributeError(f"module 'terracover.modules' has no attribute '{name}'")


# Define public API for this subpackage
__all__ = [
    # Current processing functions
    "reproject",
    "raster_colors",
    "merge_rasters",
    "convert_raster",
    "rescale_raster",
    "spectral_index",
    "raster_align",
    "raster_stack",
    "ancillary_stack",
    "raster_calculator",
    "clip_raster",
    "rasterize",
    "vectorize",
    "euclidean_distance",
    "local_stats",
    "temporal_filter",
    "transitions",
    "change_map",
    "raster_value_to_point",
    "accuracy_assessment",
    "speckle_filter",
    "raster_classification",
    "local_deforestation",
    "class_density",
    "non_allowed_transitions",
    "probability_filter",
    "reclassify",
    "fcbm",
    "leakage_belt",
    "exclusions",
    "jnr_regions",
    "python_console",
    "activity_shifting_leakage",
    "udef_arp",
]

# Module metadata
__version__ = "1.0.0"
__doc_format__ = "restructuredtext"
