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
VT7 Workflow Orchestration

This module contains workflow functions for VT7 analysis stages:
- run_testing_stage: Execute testing stage for benchmark or alternative models
- run_application_stage: Execute application stage for models

VT7 inputs (forest, non-forest, deforestation, distance maps) are generated
on-demand from the FCBM file, masked to the selected area_value.
"""

import os
import sys
import tempfile
from osgeo import gdal

# Enable GDAL exceptions for better error handling
gdal.UseExceptions()

try:
    from .folder_structure import VT7FolderStructure
    from .geometric_classification import nrt_calculation, geometric_classification, geometric_classification_alternative
    from .frequency_analysis import tabulation_bin_id, calculate_missing_bins_rf, create_relative_frequency_table, create_fit_density_map
    from .adjustment import calculate_adjustment_ratio_cnf, iterative_ar_adjustment
    from .evaluation import evaluate_testing_stage
    from .utils import admin_divisions_to_raster, read_nrt_value, build_filename, euclidean_distance, raster_calculator
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
    from terracover.modules.vt7.folder_structure import VT7FolderStructure
    from terracover.modules.vt7.geometric_classification import nrt_calculation, geometric_classification, geometric_classification_alternative
    from terracover.modules.vt7.frequency_analysis import tabulation_bin_id, calculate_missing_bins_rf, create_relative_frequency_table, create_fit_density_map
    from terracover.modules.vt7.adjustment import calculate_adjustment_ratio_cnf, iterative_ar_adjustment
    from terracover.modules.vt7.evaluation import evaluate_testing_stage
    from terracover.modules.vt7.utils import admin_divisions_to_raster, read_nrt_value, build_filename, euclidean_distance, raster_calculator


# ======================================
# VT7 Input Generation (on-demand)
# ======================================

# FCBM class expressions for generating VT7 maps
VT7_MAP_EXPRESSIONS = {
    "HRP_deforestation": "if((map1[1]==6) | (map1[1]==7) | (map1[1]==8), 1, if(map1[1]==no_data, no_data, 0))",
    "T1_forest": "if((map1[1]==5) | (map1[1]==6) | (map1[1]==7) | (map1[1]==8), 1, if(map1[1]==no_data, no_data, 0))",
    "T1_non_forest": "if((map1[1]==1) | (map1[1]==2) | (map1[1]==3) | (map1[1]==4), 1, if(map1[1]==no_data, no_data, 0))",
    "T1T2_deforestation": "if((map1[1]==6) | (map1[1]==7), 1, if(map1[1]==no_data, no_data, 0))",
    "T2_forest": "if((map1[1]==5) | (map1[1]==8), 1, if(map1[1]==no_data, no_data, 0))",
    "T2_non_forest": "if((map1[1]==1) | (map1[1]==2) | (map1[1]==3) | (map1[1]==4) | (map1[1]==6) | (map1[1]==7), 1, if(map1[1]==no_data, no_data, 0))",
    "T2T3_deforestation": "if(map1[1]==8, 1, if(map1[1]==no_data, no_data, 0))",
    "T3_forest": "if(map1[1]==5, 1, if(map1[1]==no_data, no_data, 0))",
    "T3_non_forest": "if((map1[1]==1) | (map1[1]==2) | (map1[1]==3) | (map1[1]==4) | (map1[1]==6) | (map1[1]==7) | (map1[1]==8), 1, if(map1[1]==no_data, no_data, 0))",
}


def _generate_masked_fcbm(fcbm_file, mask_file, output_file):
    """
    Generate FCBM masked to the area of interest.

    Args:
        fcbm_file: Path to FCBM file
        mask_file: Path to binary mask (1 = area of interest, 0 = outside)
        output_file: Path to output masked FCBM
    """
    expression = "if(map1[1] == 1, map2[1], no_data)"
    raster_calculator(
        input_files=[mask_file, fcbm_file],
        output_file=output_file,
        expression=expression,
        out_dtype="uint8"
    )


def _generate_vt7_map(fcbm_masked, map_name, output_file):
    """
    Generate a VT7 binary map from masked FCBM.

    Args:
        fcbm_masked: Path to masked FCBM file
        map_name: Name of the map (key in VT7_MAP_EXPRESSIONS)
        output_file: Path to output file
    """
    expression = VT7_MAP_EXPRESSIONS[map_name]
    raster_calculator(
        input_files=fcbm_masked,
        output_file=output_file,
        expression=expression,
        out_dtype="uint8"
    )


def _generate_distance_map(non_forest_file, mask_file, output_file):
    """
    Generate distance map from non-forest, masked to area of interest.

    Args:
        non_forest_file: Path to non-forest binary map
        mask_file: Path to binary mask
        output_file: Path to output distance file
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        # Calculate unmasked distance
        distance_temp = os.path.join(temp_dir, "distance_temp.tif")
        euclidean_distance(non_forest_file, distance_temp, raster_value=1)

        # Apply mask to distance
        expression = "if(map1[1] == 1, map2[1], no_data)"
        raster_calculator(
            input_files=[mask_file, distance_temp],
            output_file=output_file,
            expression=expression,
            out_dtype="float32"
        )


# ======================================
# Testing Stage
# ======================================

def run_testing_stage(folders, fcbm_file, jnr_with_exclusions_mask, admin_divisions,
                      n_classes=30, max_iterations=5, model_type='benchmark',
                      alt_etp_cal_image=None, alt_etp_cnf_image=None,
                      project_name=None, version=None,
                      run_cal=True, run_cnf=True,
                      cancel_flag=None):
    """
    Run the Testing Stage for the JNR Benchmark or Alternative Model.

    This workflow executes the Testing Stage (Fitting and Prediction phases) for either the
    Benchmark Model or Alternative Model according to Verra VT7 methodology.

    VT7 inputs are generated on-demand from the FCBM file, masked to the selected area.

    Args:
        folders: VT7FolderStructure object
        fcbm_file: Path to FCBM output file
        jnr_with_exclusions_mask: Path to binary mask (1 = analysis area, 0 = excluded)
        admin_divisions: Path to administrative divisions raster
        n_classes: Number of vulnerability classes (default: 30)
        max_iterations: Maximum iterations for AR adjustment (default: 5)
        model_type: Type of model to run: 'benchmark' or 'alternative' (default: 'benchmark')
        alt_etp_cal_image: Path to alternative ETP CAL image (required if model_type='alternative' and run_cal=True)
        alt_etp_cnf_image: Path to alternative ETP CNF image (required if model_type='alternative' and run_cnf=True)
        project_name: Project name to prepend to output filenames (default: None)
        version: Version identifier to append to output filenames (default: None)
        run_cal: Whether to run the Calibration (CAL) phase (default: True)
        run_cnf: Whether to run the Confirmation (CNF) phase (default: True)
        cancel_flag: Optional callback function that returns True to cancel operation

    Returns:
        dict: Dictionary containing key outputs and paths

    Raises:
        RuntimeError: If operation is cancelled by user
    """

    # Helper function to check cancellation
    def _check_cancel():
        if cancel_flag and cancel_flag():
            raise RuntimeError("Operation cancelled by user")

    _check_cancel()

    # Validate model_type
    if model_type not in ['benchmark', 'alternative']:
        raise ValueError(f"Invalid model_type: {model_type}. Must be 'benchmark' or 'alternative'")

    # Validate at least one phase is selected
    if not run_cal and not run_cnf:
        raise ValueError("At least one phase (run_cal or run_cnf) must be True")

    # Validate alternative model inputs based on selected phases
    if model_type == 'alternative':
        if run_cal and alt_etp_cal_image is None:
            raise ValueError("alt_etp_cal_image is required when model_type='alternative' and run_cal=True")
        if run_cnf and alt_etp_cnf_image is None:
            raise ValueError("alt_etp_cnf_image is required when model_type='alternative' and run_cnf=True")

    # Determine folders and prefix based on model type
    if model_type == 'benchmark':
        folders.create_testing_models(bcm_cal=run_cal, bcm_cnf=run_cnf)
        fitting_folder = folders.testing_benchmark_fitting
        prediction_folder = folders.testing_benchmark_prediction
        prefix = "BCM"
        model_name = "Benchmark Model"
    else:
        folders.create_testing_models(alt_cal=run_cal, alt_cnf=run_cnf)
        fitting_folder = folders.testing_alternative_fitting
        prediction_folder = folders.testing_alternative_prediction
        prefix = "ALT"
        model_name = "Alternative Model"

    # Initialize result variables
    nrt = None
    fitting_density_map_cal = None
    adjusted_prediction_density_map_cnf = None
    frequency_table_cal_df = None
    frequency_table_cal = None

    # Use a persistent temp directory for VT7 inputs that need to be shared between phases
    with tempfile.TemporaryDirectory() as vt7_temp_dir:
        # Generate masked FCBM
        fcbm_masked = os.path.join(vt7_temp_dir, "fcbm_masked.tif")
        _generate_masked_fcbm(fcbm_file, jnr_with_exclusions_mask, fcbm_masked)
        _check_cancel()

        # Generate deforestation maps (needed for frequency tables)
        t1t2_deforestation = os.path.join(vt7_temp_dir, "T1T2_deforestation.tif")
        t2t3_deforestation = os.path.join(vt7_temp_dir, "T2T3_deforestation.tif")
        _generate_vt7_map(fcbm_masked, "T1T2_deforestation", t1t2_deforestation)
        _check_cancel()
        _generate_vt7_map(fcbm_masked, "T2T3_deforestation", t2t3_deforestation)
        _check_cancel()

        ######### 1- Fitting Phase (CAL) #########
        if run_cal:
            print("="*60)
            print(f"Running {model_name} - Calibration Phase (CAL)...")
            print("="*60)

            if model_type == 'benchmark':
                # Generate T1 non-forest and distance
                t1_non_forest = os.path.join(vt7_temp_dir, "T1_non_forest.tif")
                _generate_vt7_map(fcbm_masked, "T1_non_forest", t1_non_forest)

                t1_distance_cal = os.path.join(fitting_folder, build_filename("00_BCM_T1_distance_CAL.tif", project_name, version))
                _generate_distance_map(t1_non_forest, jnr_with_exclusions_mask, t1_distance_cal)

                # Generate HRP deforestation for NRT calculation
                hrp_deforestation = os.path.join(vt7_temp_dir, "HRP_deforestation.tif")
                _generate_vt7_map(fcbm_masked, "HRP_deforestation", hrp_deforestation)

                vulnerability_cal_name = build_filename(f"04_{prefix}_Vulnerability_CAL.tif", project_name, version)
                vulnerability_cal = os.path.join(fitting_folder, vulnerability_cal_name)
                nrt = nrt_calculation(t1_distance_cal, hrp_deforestation, jnr_with_exclusions_mask, fitting_folder, project_name, version)
                nrt_txt_name = build_filename("03_BCM_NRT_value.txt", project_name, version)
                nrt_txt = os.path.join(fitting_folder, nrt_txt_name)
                geometric_classification(t1_distance_cal, vulnerability_cal, nrt, n_classes, nrt_txt=nrt_txt)
            else:  # alternative
                t1_forest = os.path.join(vt7_temp_dir, "T1_forest.tif")
                _generate_vt7_map(fcbm_masked, "T1_forest", t1_forest)

                vulnerability_cal_name = build_filename(f"01_{prefix}_Vulnerability_CAL.tif", project_name, version)
                vulnerability_cal = os.path.join(fitting_folder, vulnerability_cal_name)
                geometric_classification_alternative(alt_etp_cal_image, n_classes, jnr_with_exclusions_mask, t1_forest, vulnerability_cal)
                nrt = None

            # Step 2: Create the Modeling Regions Map
            modelling_regions_cal_name = build_filename(f"0{'5' if model_type == 'benchmark' else '2'}_{prefix}_Modeling_Regions_CAL.tif", project_name, version)
            modelling_regions_cal = os.path.join(fitting_folder, modelling_regions_cal_name)
            modelling_regions_cal_array = tabulation_bin_id(vulnerability_cal, admin_divisions, modelling_regions_cal)

            # Step 3: Create the Relative Frequency Table
            frequency_map_cal_name = build_filename(f"0{'6' if model_type == 'benchmark' else '3'}_{prefix}_Relative_Frequency_Map_CAL.tif", project_name, version)
            frequency_map_cal = os.path.join(fitting_folder, frequency_map_cal_name)
            frequency_table_cal_name = build_filename(f"0{'6' if model_type == 'benchmark' else '3'}_{prefix}_Relative_Frequency_Table_CAL.xlsx", project_name, version)
            frequency_table_cal = os.path.join(fitting_folder, frequency_table_cal_name)
            frequency_table_cal_df = create_relative_frequency_table(modelling_regions_cal_array, t1t2_deforestation, frequency_table_cal, frequency_map_cal)

            # Step 4: Create the Fitting Density Map
            fitting_density_map_cal_name = build_filename(f"0{'7' if model_type == 'benchmark' else '4'}_{prefix}_Fitting_Density_Map_CAL.tif", project_name, version)
            fitting_density_map_cal = os.path.join(fitting_folder, fitting_density_map_cal_name)
            create_fit_density_map(risk30=vulnerability_cal,
                                   tabulation_bin_id_masked=modelling_regions_cal_array,
                                   merged_df=frequency_table_cal_df,
                                   out_fn2=fitting_density_map_cal)
            _check_cancel()

            print(f"Calibration Phase (CAL) - {model_name} COMPLETED")
            print("="*60 + "\n")

        ######### 2- Prediction Phase (CNF) #########
        if run_cnf:
            _check_cancel()
            print("="*60)
            print(f"Running {model_name} - Confirmation Phase (CNF)...")
            print("="*60)

            # If CAL was not run in this call, load the frequency table from file
            if frequency_table_cal_df is None:
                import pandas as pd
                frequency_table_cal_name = build_filename(f"0{'6' if model_type == 'benchmark' else '3'}_{prefix}_Relative_Frequency_Table_CAL.xlsx", project_name, version)
                frequency_table_cal = os.path.join(fitting_folder, frequency_table_cal_name)
                if not os.path.exists(frequency_table_cal):
                    raise FileNotFoundError(
                        f"CNF phase requires CAL outputs. Frequency table not found: {frequency_table_cal}. "
                        f"Run CAL phase first or select it in this run."
                    )
                frequency_table_cal_df = pd.read_excel(frequency_table_cal)

            # Also need NRT for benchmark CNF if CAL was not run
            if model_type == 'benchmark' and nrt is None:
                nrt_file_name = build_filename("03_BCM_NRT_value.txt", project_name, version)
                nrt_file = os.path.join(fitting_folder, nrt_file_name)
                nrt = read_nrt_value(nrt_file)

            if model_type == 'benchmark':
                # Generate T2 non-forest and distance
                t2_non_forest = os.path.join(vt7_temp_dir, "T2_non_forest.tif")
                _generate_vt7_map(fcbm_masked, "T2_non_forest", t2_non_forest)

                t2_distance_cnf = os.path.join(prediction_folder, build_filename("00_BCM_T2_distance_CNF.tif", project_name, version))
                _generate_distance_map(t2_non_forest, jnr_with_exclusions_mask, t2_distance_cnf)

                vulnerability_cnf_name = build_filename(f"01_{prefix}_Vulnerability_CNF.tif", project_name, version)
                vulnerability_cnf = os.path.join(prediction_folder, vulnerability_cnf_name)
                geometric_classification(t2_distance_cnf, vulnerability_cnf, nrt, n_classes)
            else:  # alternative
                t2_forest = os.path.join(vt7_temp_dir, "T2_forest.tif")
                _generate_vt7_map(fcbm_masked, "T2_forest", t2_forest)

                vulnerability_cnf_name = build_filename(f"01_{prefix}_Vulnerability_CNF.tif", project_name, version)
                vulnerability_cnf = os.path.join(prediction_folder, vulnerability_cnf_name)
                geometric_classification_alternative(alt_etp_cnf_image, n_classes, jnr_with_exclusions_mask, t2_forest, vulnerability_cnf)

            modelling_regions_cnf_name = build_filename(f"02_{prefix}_Modeling_Regions_CNF.tif", project_name, version)
            modelling_regions_cnf = os.path.join(prediction_folder, modelling_regions_cnf_name)
            modelling_regions_cnf_array = tabulation_bin_id(vulnerability_cnf, admin_divisions, modelling_regions_cnf)

            # Check for missing bins and update frequency table if needed
            frequency_table_cal_df = calculate_missing_bins_rf(frequency_table_cal_df,
                                                                modelling_regions_cnf_array,
                                                                frequency_table_cal)

            # Step 2: Create the Prediction Density Map
            prediction_density_map_cnf_name = build_filename(f"03_{prefix}_Prediction_Density_Map_CNF.tif", project_name, version)
            prediction_density_map_cnf = os.path.join(prediction_folder, prediction_density_map_cnf_name)
            prediction_density_map_cnf_arr = create_fit_density_map(risk30=vulnerability_cnf,
                                                                    tabulation_bin_id_masked=modelling_regions_cnf_array,
                                                                    merged_df=frequency_table_cal_df,
                                                                    out_fn2=prediction_density_map_cnf)

            # Step 3: Calculate Adjustment Ratio (AR) in CNF
            _check_cancel()
            adjusted_prediction_density_map_cnf_name = build_filename(f"04_{prefix}_Adjusted_Prediction_Density_Map_CNF.tif", project_name, version)
            adjusted_prediction_density_map_cnf = os.path.join(prediction_folder, adjusted_prediction_density_map_cnf_name)
            ar_log_cnf_name = build_filename(f"05_{prefix}_AR_log_CNF.txt", project_name, version)
            ar_log_cnf = os.path.join(prediction_folder, ar_log_cnf_name)
            iterative_ar_adjustment(prediction_density_map_cnf_arr,
                                    vulnerability_cnf,
                                    adjusted_prediction_density_map_cnf,
                                    ar_log_cnf,
                                    deforestation_cnf=t2t3_deforestation,
                                    max_iterations=max_iterations)
            _check_cancel()

            print(f"Confirmation Phase (CNF) - {model_name} COMPLETED")
            print("="*60 + "\n")

    # Build completion message
    phases_run = []
    if run_cal:
        phases_run.append("CAL")
    if run_cnf:
        phases_run.append("CNF")
    print("="*60)
    print(f"Testing Stage - {model_name} ({', '.join(phases_run)}) COMPLETED SUCCESSFULLY")
    print("="*60 + "\n")

    # Return key outputs
    return {
        'nrt': nrt,
        'fitting_density_map_cal': fitting_density_map_cal,
        'adjusted_prediction_density_map_cnf': adjusted_prediction_density_map_cnf,
        'frequency_table_cal_df': frequency_table_cal_df
    }


# ======================================
# Application Stage
# ======================================

def run_application_stage(folders, fcbm_file, jnr_with_exclusions_mask, admin_divisions,
                          n_classes=30, max_iterations=5, expected_deforestation=None,
                          model_type='benchmark', alt_etp_hrp_image=None, alt_etp_vp_image=None,
                          project_name=None, version=None,
                          run_hrp=True, run_vp=True, vp_years=None,
                          cancel_flag=None):
    """
    Run the Application Stage for the Benchmark or Alternative Model.

    This workflow executes the Application Stage (Fitting and Prediction phases) for either the
    Benchmark Model or Alternative Model according to Verra VT7 methodology.

    VT7 inputs are generated on-demand from the FCBM file, masked to the selected area.

    Note: For Benchmark Model, the NRT value is automatically read from the Testing Stage output.

    Args:
        folders: VT7FolderStructure object
        fcbm_file: Path to FCBM output file
        jnr_with_exclusions_mask: Path to binary mask (1 = analysis area, 0 = excluded)
        admin_divisions: Path to administrative divisions raster
        n_classes: Number of vulnerability classes (default: 30)
        max_iterations: Maximum iterations for AR adjustment (default: 5)
        expected_deforestation: Expected deforestation in hectares for VP phase (optional)
        model_type: Type of model to run: 'benchmark' or 'alternative' (default: 'benchmark')
        alt_etp_hrp_image: Path to alternative ETP HRP image (required if model_type='alternative' and run_hrp=True)
        alt_etp_vp_image: Path to alternative ETP VP image (required if model_type='alternative' and run_vp=True)
        project_name: Project name to prepend to output filenames (default: None)
        version: Version identifier to append to output filenames (default: None)
        run_hrp: Whether to run the Historical Reference Period (HRP) phase (default: True)
        run_vp: Whether to run the Validity Period (VP) phase (default: True)
        vp_years: Length of the Validity Period in years (required). The VP output will be
                  converted to annual deforestation rate (ha/year per pixel) following VT0007
                  methodology. Must be a positive integer > 0.
        cancel_flag: Optional callback function that returns True to cancel operation

    Returns:
        dict: Dictionary containing key outputs and paths

    Raises:
        RuntimeError: If operation is cancelled by user
    """

    # Helper function to check cancellation
    def _check_cancel():
        if cancel_flag and cancel_flag():
            raise RuntimeError("Operation cancelled by user")

    _check_cancel()

    # Validate model_type
    if model_type not in ['benchmark', 'alternative']:
        raise ValueError(f"Invalid model_type: {model_type}. Must be 'benchmark' or 'alternative'")

    # Validate at least one phase is selected
    if not run_hrp and not run_vp:
        raise ValueError("At least one phase (run_hrp or run_vp) must be True")

    # Validate alternative model inputs
    if model_type == 'alternative':
        if run_hrp and alt_etp_hrp_image is None:
            raise ValueError("alt_etp_hrp_image is required when model_type='alternative' and run_hrp=True")
        if run_vp and alt_etp_vp_image is None:
            raise ValueError("alt_etp_vp_image is required when model_type='alternative' and run_vp=True")

    # Determine folders and prefix based on model type
    if model_type == 'benchmark':
        folders.create_application_models(bcm_hrp=run_hrp, bcm_vp=run_vp)
        fitting_folder = folders.application_benchmark_fitting
        prediction_folder = folders.application_benchmark_prediction
        prefix = "BCM"
        model_name = "Benchmark Model"
    else:
        folders.create_application_models(alt_hrp=run_hrp, alt_vp=run_vp)
        fitting_folder = folders.application_alternative_fitting
        prediction_folder = folders.application_alternative_prediction
        prefix = "ALT"
        model_name = "Alternative Model"

    # Initialize result variables
    nrt = None
    fitting_density_map_hrp = None
    adjusted_prediction_density_map_vp = None
    frequency_table_hrp_df = None
    frequency_table_hrp = None

    # Read NRT value from Testing Stage for Benchmark Model
    if model_type == 'benchmark':
        nrt_file_name = build_filename("03_BCM_NRT_value.txt", project_name, version)
        nrt_file = os.path.join(folders.testing_benchmark_fitting, nrt_file_name)
        nrt = read_nrt_value(nrt_file)
        print(f"NRT value read from Testing Stage: {nrt} meters")

    # Use a persistent temp directory for VT7 inputs
    with tempfile.TemporaryDirectory() as vt7_temp_dir:
        # Generate masked FCBM
        fcbm_masked = os.path.join(vt7_temp_dir, "fcbm_masked.tif")
        _generate_masked_fcbm(fcbm_file, jnr_with_exclusions_mask, fcbm_masked)
        _check_cancel()

        # Generate HRP deforestation (needed for frequency table)
        hrp_deforestation = os.path.join(vt7_temp_dir, "HRP_deforestation.tif")
        _generate_vt7_map(fcbm_masked, "HRP_deforestation", hrp_deforestation)
        _check_cancel()

        ######### 1- Fitting Phase (HRP) #########
        if run_hrp:
            print("="*60)
            print(f"Running {model_name} - Historical Reference Period (HRP)...")
            print("="*60)

            if model_type == 'benchmark':
                # Generate T1 non-forest and distance
                t1_non_forest = os.path.join(vt7_temp_dir, "T1_non_forest.tif")
                _generate_vt7_map(fcbm_masked, "T1_non_forest", t1_non_forest)

                t1_distance_hrp = os.path.join(fitting_folder, build_filename("00_BCM_T1_distance_HRP.tif", project_name, version))
                _generate_distance_map(t1_non_forest, jnr_with_exclusions_mask, t1_distance_hrp)

                vulnerability_hrp_name = build_filename(f"01_{prefix}_Vulnerability_HRP.tif", project_name, version)
                vulnerability_hrp = os.path.join(fitting_folder, vulnerability_hrp_name)
                geometric_classification(t1_distance_hrp, vulnerability_hrp, nrt, n_classes)
            else:  # alternative
                t1_forest = os.path.join(vt7_temp_dir, "T1_forest.tif")
                _generate_vt7_map(fcbm_masked, "T1_forest", t1_forest)

                vulnerability_hrp_name = build_filename(f"01_{prefix}_Vulnerability_HRP.tif", project_name, version)
                vulnerability_hrp = os.path.join(fitting_folder, vulnerability_hrp_name)
                geometric_classification_alternative(alt_etp_hrp_image, n_classes, jnr_with_exclusions_mask, t1_forest, vulnerability_hrp)

            # Step 2: Create the Modeling Regions Map
            modelling_regions_hrp_name = build_filename(f"02_{prefix}_Modeling_Regions_HRP.tif", project_name, version)
            modelling_regions_hrp = os.path.join(fitting_folder, modelling_regions_hrp_name)
            modelling_regions_hrp_array = tabulation_bin_id(vulnerability_hrp, admin_divisions, modelling_regions_hrp)

            # Step 3: Create the Relative Frequency Table
            frequency_map_hrp_name = build_filename(f"03_{prefix}_Relative_Frequency_Map_HRP.tif", project_name, version)
            frequency_map_hrp = os.path.join(fitting_folder, frequency_map_hrp_name)
            frequency_table_hrp_name = build_filename(f"03_{prefix}_Relative_Frequency_Table_HRP.xlsx", project_name, version)
            frequency_table_hrp = os.path.join(fitting_folder, frequency_table_hrp_name)
            frequency_table_hrp_df = create_relative_frequency_table(modelling_regions_hrp_array, hrp_deforestation, frequency_table_hrp, frequency_map_hrp)

            # Step 4: Create the Fitting Density Map
            fitting_density_map_hrp_name = build_filename(f"04_{prefix}_Fitting_Density_Map_HRP.tif", project_name, version)
            fitting_density_map_hrp = os.path.join(fitting_folder, fitting_density_map_hrp_name)
            create_fit_density_map(risk30=vulnerability_hrp,
                                   tabulation_bin_id_masked=modelling_regions_hrp_array,
                                   merged_df=frequency_table_hrp_df,
                                   out_fn2=fitting_density_map_hrp)
            _check_cancel()

            print(f"Historical Reference Period (HRP) - {model_name} COMPLETED")
            print("="*60 + "\n")

        ######### 2- Prediction Phase (VP) #########
        if run_vp:
            _check_cancel()
            print("="*60)
            print(f"Running {model_name} - Validity Period (VP)...")
            print("="*60)

            # If HRP was not run in this call, load the frequency table from file
            if frequency_table_hrp_df is None:
                import pandas as pd
                frequency_table_hrp_name = build_filename(f"03_{prefix}_Relative_Frequency_Table_HRP.xlsx", project_name, version)
                frequency_table_hrp = os.path.join(fitting_folder, frequency_table_hrp_name)
                if not os.path.exists(frequency_table_hrp):
                    raise FileNotFoundError(
                        f"VP phase requires HRP outputs. Frequency table not found: {frequency_table_hrp}. "
                        f"Run HRP phase first or select it in this run."
                    )
                frequency_table_hrp_df = pd.read_excel(frequency_table_hrp)

            if model_type == 'benchmark':
                # Generate T3 non-forest and distance
                t3_non_forest = os.path.join(vt7_temp_dir, "T3_non_forest.tif")
                _generate_vt7_map(fcbm_masked, "T3_non_forest", t3_non_forest)

                t3_distance_vp = os.path.join(prediction_folder, build_filename("00_BCM_T3_distance_VP.tif", project_name, version))
                _generate_distance_map(t3_non_forest, jnr_with_exclusions_mask, t3_distance_vp)

                vulnerability_vp_name = build_filename(f"01_{prefix}_Vulnerability_VP.tif", project_name, version)
                vulnerability_vp = os.path.join(prediction_folder, vulnerability_vp_name)
                geometric_classification(t3_distance_vp, vulnerability_vp, nrt, n_classes)
            else:  # alternative
                t3_forest = os.path.join(vt7_temp_dir, "T3_forest.tif")
                _generate_vt7_map(fcbm_masked, "T3_forest", t3_forest)

                vulnerability_vp_name = build_filename(f"01_{prefix}_Vulnerability_VP.tif", project_name, version)
                vulnerability_vp = os.path.join(prediction_folder, vulnerability_vp_name)
                geometric_classification_alternative(alt_etp_vp_image, n_classes, jnr_with_exclusions_mask, t3_forest, vulnerability_vp)

            modelling_regions_vp_name = build_filename(f"02_{prefix}_Modeling_Regions_VP.tif", project_name, version)
            modelling_regions_vp = os.path.join(prediction_folder, modelling_regions_vp_name)
            modelling_regions_vp_array = tabulation_bin_id(vulnerability_vp, admin_divisions, modelling_regions_vp)

            # Check for missing bins and update frequency table if needed
            frequency_table_hrp_df = calculate_missing_bins_rf(frequency_table_hrp_df,
                                                                modelling_regions_vp_array,
                                                                frequency_table_hrp)

            # Step 2: Create the Prediction Density Map
            prediction_density_map_vp_name = build_filename(f"03_{prefix}_Prediction_Density_Map_VP.tif", project_name, version)
            prediction_density_map_vp = os.path.join(prediction_folder, prediction_density_map_vp_name)
            prediction_density_map_vp_arr = create_fit_density_map(risk30=vulnerability_vp,
                                                                   tabulation_bin_id_masked=modelling_regions_vp_array,
                                                                   merged_df=frequency_table_hrp_df,
                                                                   out_fn2=prediction_density_map_vp)

            # Step 3: Calculate Adjustment Ratio (AR) in VP
            _check_cancel()
            adjusted_prediction_density_map_vp_name = build_filename(f"04_{prefix}_Adjusted_Prediction_Density_Map_VP.tif", project_name, version)
            adjusted_prediction_density_map_vp = os.path.join(prediction_folder, adjusted_prediction_density_map_vp_name)
            ar_log_vp_name = build_filename(f"05_{prefix}_AR_log_VP.txt", project_name, version)
            ar_log_vp = os.path.join(prediction_folder, ar_log_vp_name)
            iterative_ar_adjustment(prediction_density_map_vp_arr,
                                    vulnerability_vp,
                                    adjusted_prediction_density_map_vp,
                                    ar_log_vp,
                                    max_iterations=max_iterations,
                                    expected_deforestation=expected_deforestation,
                                    vp_years=vp_years)
            _check_cancel()

            print(f"Validity Period (VP) - {model_name} COMPLETED")
            print("="*60 + "\n")

    # Build completion message
    phases_run = []
    if run_hrp:
        phases_run.append("HRP")
    if run_vp:
        phases_run.append("VP")
    print("="*60)
    print(f"Application Stage - {model_name} ({', '.join(phases_run)}) COMPLETED SUCCESSFULLY")
    print("="*60 + "\n")

    # Return key outputs
    return {
        'frequency_table_hrp_df': frequency_table_hrp_df,
        'fitting_density_map_hrp': fitting_density_map_hrp,
        'adjusted_prediction_density_map_vp': adjusted_prediction_density_map_vp
    }
