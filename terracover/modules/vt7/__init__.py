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
VT7 (Vulnerability Mapping Tool 7) Package

This package provides a complete implementation of the VT7 methodology for
forest vulnerability mapping and deforestation risk assessment.

Modules:
--------
- utils: Utility functions for raster/vector processing
- folder_structure: Folder structure management
- geometric_classification: NRT calculation and geometric classification
- frequency_analysis: Frequency tables and tabulation
- adjustment: Adjustment ratio calculations and iterative adjustments
- evaluation: Model evaluation and performance analysis
- workflow: Main workflow orchestration functions

Main Classes:
-------------
- VT7FolderStructure: Manages VT7 folder structure
- ModelEvaluation: Performs model evaluation and analysis

Main Functions:
---------------
- run_testing_stage: Execute testing stage for models
- run_application_stage: Execute application stage for models
- evaluate_testing_stage: Evaluate model performance

For complete workflow orchestration with GUI support and data conversions,
use the udef_arp function from terracover.modules.udef_arp.

Usage Example:
--------------
from terracover.modules.udef_arp import udef_arp

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
"""

import sys
import os

# Try relative imports first (when used as package), fallback to absolute imports
try:
    # Import utilities
    from .utils import (
        image_to_array,
        array_to_image,
        apply_mask_to_raster,
        vector_to_raster,
        admin_divisions_to_raster,
        convert_expression_to_numpy,
        raster_calculator,
        euclidean_distance,
        replace_ref_system
    )

    # Import folder structure management
    from .folder_structure import VT7FolderStructure

    # Import geometric classification
    from .geometric_classification import (
        nrt_calculation,
        geometric_classification,
        geometric_classification_alternative
    )

    # Import frequency analysis
    from .frequency_analysis import (
        tabulation_bin_id,
        calculate_missing_bins_rf,
        create_relative_frequency_table,
        create_fit_density_map
    )

    # Import adjustment functions
    from .adjustment import (
        calculate_adjustment_ratio_cnf,
        adjusted_prediction_density_array,
        iterative_ar_adjustment
    )

    # Import evaluation
    from .evaluation import (
        ModelEvaluation,
        evaluate_testing_stage
    )

    # Import workflow functions
    from .workflow import (
        run_testing_stage,
        run_application_stage
    )

except ImportError:
    # Fallback to absolute imports
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    from terracover.modules.vt7.utils import (
        image_to_array,
        array_to_image,
        apply_mask_to_raster,
        vector_to_raster,
        admin_divisions_to_raster,
        convert_expression_to_numpy,
        raster_calculator,
        euclidean_distance,
        replace_ref_system
    )

    from terracover.modules.vt7.folder_structure import VT7FolderStructure

    from terracover.modules.vt7.geometric_classification import (
        nrt_calculation,
        geometric_classification,
        geometric_classification_alternative
    )

    from terracover.modules.vt7.frequency_analysis import (
        tabulation_bin_id,
        calculate_missing_bins_rf,
        create_relative_frequency_table,
        create_fit_density_map
    )

    from terracover.modules.vt7.adjustment import (
        calculate_adjustment_ratio_cnf,
        adjusted_prediction_density_array,
        iterative_ar_adjustment
    )

    from terracover.modules.vt7.evaluation import (
        ModelEvaluation,
        evaluate_testing_stage
    )

    from terracover.modules.vt7.workflow import (
        run_testing_stage,
        run_application_stage
    )

# Define public API
__all__ = [
    # Utilities
    'image_to_array',
    'array_to_image',
    'apply_mask_to_raster',
    'vector_to_raster',
    'admin_divisions_to_raster',
    'raster_calculator',
    'euclidean_distance',

    # Classes
    'VT7FolderStructure',
    'ModelEvaluation',

    # Main workflow functions
    'run_testing_stage',
    'run_application_stage',
    'evaluate_testing_stage',

    # Geometric classification
    'nrt_calculation',
    'geometric_classification',
    'geometric_classification_alternative',

    # Frequency analysis
    'tabulation_bin_id',
    'calculate_missing_bins_rf',
    'create_relative_frequency_table',
    'create_fit_density_map',

    # Adjustment
    'calculate_adjustment_ratio_cnf',
    'adjusted_prediction_density_array',
    'iterative_ar_adjustment'
]

__version__ = '1.0.0'
__author__ = 'david.montoya@terraglobalcapital.com'
