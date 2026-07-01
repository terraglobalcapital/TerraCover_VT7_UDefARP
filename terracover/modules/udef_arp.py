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
VT7 User-Defined Alternative Risk Proxy (UDEF_ARP) GUI Module

This module provides a GUI interface for running VT7 vulnerability mapping analysis.
All functionality has been modularized in the vt7 package for better maintainability.

The vt7 package is organized as follows:
- vt7.utils: Utility functions for raster/vector processing
- vt7.folder_structure: Folder structure management
- vt7.geometric_classification: NRT and geometric classification
- vt7.frequency_analysis: Frequency tables and tabulation
- vt7.adjustment: Adjustment ratio calculations
- vt7.evaluation: Model evaluation and performance analysis
- vt7.workflow: Main workflow orchestration
"""
# Configure DLL paths when running as main script (before any imports that might load DLLs)
if __name__ == "__main__":
    import sys
    import os
    _terracover_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    if _terracover_path not in sys.path:
        sys.path.insert(0, _terracover_path)
    from terracover.core.setup_environment import setup_dll_paths, is_environment_configured
    if not is_environment_configured():
        setup_dll_paths()
    del _terracover_path
    
import sys
import os
import json
import shutil
from typing import Dict, Any, List, Optional, Callable
from osgeo import gdal
import tempfile

# Import GUI base class and VT7 modules
try:
    from ..core.gui_base import FuncInputsBase
    from ..core.base_processor import BaseFileProcessor
    from ..core.validations import (
        _SpatialFileValidator,
        _FolderValidator,
        _FileOverwriteValidator
    )
    from ..core.message_boxes import _ask_yes_no_messagebox
    from ..core.data_converters import TextEntryConverter
    from .vt7.folder_structure import VT7FolderStructure
    from .vt7.evaluation import evaluate_testing_stage
    from .vt7.utils import admin_divisions_to_raster, raster_calculator
    from .vt7.workflow import run_testing_stage, run_application_stage
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from terracover.core.gui_base import FuncInputsBase
    from terracover.core.base_processor import BaseFileProcessor
    from terracover.core.validations import (
        _SpatialFileValidator,
        _FolderValidator,
        _FileOverwriteValidator
    )
    from terracover.core.message_boxes import _ask_yes_no_messagebox
    from terracover.core.data_converters import TextEntryConverter
    from terracover.modules.vt7.folder_structure import VT7FolderStructure
    from terracover.modules.vt7.evaluation import evaluate_testing_stage
    from terracover.modules.vt7.utils import admin_divisions_to_raster, raster_calculator
    from terracover.modules.vt7.workflow import run_testing_stage, run_application_stage


# ------------------------------------------------------------------------
# Processor Class
# ------------------------------------------------------------------------

class _UdefArpProcessor(BaseFileProcessor):
    """Processor for VT7 UDEF_ARP workflow."""

    def __init__(self,
                 fcbm_file: str,
                 exclusions: str,
                 admin_divisions: str,
                 area_of_interest: str,
                 output_vt7_folder: str,
                 area_value: int = 1,
                 alt_etp_cal_image: Optional[str] = None,
                 alt_etp_cnf_image: Optional[str] = None,
                 alt_etp_hrp_image: Optional[str] = None,
                 alt_etp_vp_image: Optional[str] = None,
                 expected_deforestation: Optional[float] = None,
                 max_iterations: int = 5,
                 evaluation_grid_area: float = 100000,
                 vp_years: Optional[int] = None,
                 project_name: Optional[str] = None,
                 version: Optional[str] = None,
                 workflow_stages: Optional[str] = None,
                 progress_callback: Optional[Callable[[str, float], None]] = None,
                 cancel_flag: Optional[Callable[[], bool]] = None,
                 show_progress: bool = True,
                 **kwargs) -> None:
        """
        Initialize the VT7 UDEF_ARP processor.

        Args:
            fcbm_file: Path to Forest Cover Benchmark Model raster
            exclusions: Path to exclusions mask raster (1=excluded areas, 0 or other values=included areas)
            admin_divisions: Path to administrative divisions file (vector or raster)
            area_of_interest: Path to area of interest mask raster (complete area WITHOUT exclusions removed).
                Must be an integer raster where valid regions have values > 0 (e.g., 1, 50, 100).
                Pixels with value 0 or NoData are excluded from processing.
            area_value: Value in area_of_interest raster that defines the specific analysis area (default: 1).
                Only pixels matching this value will be processed.
            output_vt7_folder: Output folder for VT7 results
            alt_etp_cal_image: Alternative ETP calibration image (optional)
            alt_etp_cnf_image: Alternative ETP confirmation image (optional)
            alt_etp_hrp_image: Alternative ETP historical reference period image (optional)
            alt_etp_vp_image: Alternative ETP validation period image (optional)
            expected_deforestation: Expected deforestation area in hectares (required for VP stages)
            max_iterations: Maximum iterations for adjustment (default: 5)
            evaluation_grid_area: Grid area for evaluation in hectares (default: 100000)
            vp_years: Length of the Validity Period in years (required). The VP output will be
                converted to annual deforestation rate (ha/year per pixel) following VT0007
                methodology. Must be a positive integer > 0.
            project_name: Project name to prepend to output filenames (default: None)
            version: Version identifier to append to output filenames (default: None)
            workflow_stages: List of workflow stages to execute
            progress_callback: Callback function for progress updates
            cancel_flag: Function to check for user cancellation
            show_progress: Display progress messages
        """
        # Initialize base class with fcbm_file as input and output_vt7_folder as output
        super().__init__(
            input_file=fcbm_file,
            input_files=None,
            output_file=output_vt7_folder,
            suffix="",
            show_progress=show_progress,
            progress_callback=progress_callback,
            cancel_flag=cancel_flag
        )

        # Required file paths
        self.fcbm_file = fcbm_file
        self.output_vt7_folder = output_vt7_folder
        self.exclusions = exclusions
        self.admin_divisions = admin_divisions
        self.area_of_interest = area_of_interest

        # Detect if admin_divisions is a raster or vector file
        self._admin_divisions_is_raster = self._is_raster_file(admin_divisions)

        # Internal variable for inverted binary mask (will be created in processing)
        self._jnr_with_exclusions_mask_temp = None
        self._admin_divisions_raster_temp = None

        # Optional ETP images for alternative model
        self.alt_etp_cal_image = alt_etp_cal_image if alt_etp_cal_image else ''
        self.alt_etp_cnf_image = alt_etp_cnf_image if alt_etp_cnf_image else ''
        self.alt_etp_hrp_image = alt_etp_hrp_image if alt_etp_hrp_image else ''
        self.alt_etp_vp_image = alt_etp_vp_image if alt_etp_vp_image else ''

        # Numeric parameters
        self.area_value = int(area_value)
        self.expected_deforestation = float(expected_deforestation) if expected_deforestation not in (None, '') else None
        self.max_iterations = int(max_iterations)
        self.evaluation_grid_area = float(evaluation_grid_area)
        self.vp_years = int(vp_years) if vp_years not in (None, '') else None

        # File naming parameters
        self.project_name = project_name if project_name else None
        self.version = version if version else None

        # Workflow stages from checkbox field
        if workflow_stages is None:
            workflow_stages = []
        if isinstance(workflow_stages, str):
            workflow_stages = json.loads(workflow_stages)

        # Benchmark Model (BCM) - Testing Stage
        self.bcm_cal = "BCM Calibration (CAL)" in workflow_stages
        self.bcm_cnf = "BCM Confirmation (CNF)" in workflow_stages
        self.bcm_eval_cal = "BCM Evaluation CAL" in workflow_stages
        self.bcm_eval_cnf = "BCM Evaluation CNF" in workflow_stages

        # Benchmark Model (BCM) - Application Stage
        self.bcm_hrp = "BCM Historical Reference (HRP)" in workflow_stages
        self.bcm_vp = "BCM Validity Period (VP)" in workflow_stages

        # Alternative Model (ALT) - Testing Stage
        self.alt_cal = "ALT Calibration (CAL)" in workflow_stages
        self.alt_cnf = "ALT Confirmation (CNF)" in workflow_stages
        self.alt_eval_cal = "ALT Evaluation CAL" in workflow_stages
        self.alt_eval_cnf = "ALT Evaluation CNF" in workflow_stages

        # Alternative Model (ALT) - Application Stage
        self.alt_hrp = "ALT Historical Reference (HRP)" in workflow_stages
        self.alt_vp = "ALT Validity Period (VP)" in workflow_stages

    @staticmethod
    def _is_raster_file(file_path: str) -> bool:
        """Check if a file path has a raster extension (.tif, .tiff)."""
        if not file_path:
            return False
        return os.path.splitext(file_path)[1].lower() in {'.tif', '.tiff'}

    def _validation(self) -> List[str]:
        """
        Validate all inputs for the VT7 workflow.

        Returns
        -------
        List[str]
            List of validation error messages. Empty if no errors.
        """
        from terracover.modules.vt7.utils import build_filename
        errors = []

        # Check for cancellation
        if self._check_cancellation_with_error(errors):
            return errors

        # Validate numeric parameters
        if not isinstance(self.area_value, int) or self.area_value < 0:
            errors.append(f"Area value must be a non-negative integer, got: {self.area_value}")

        # Validate required raster inputs
        raster_validator = _SpatialFileValidator()

        # FCBM file (required) - must have projected CRS
        # All other rasters must match FCBM's CRS through alignment validation
        self._update_progress("Validating FCBM file", 0.06)
        fcbm_errors = raster_validator.validate_raster_file(
            self.fcbm_file,
            require_projected=True
        )
        if fcbm_errors:
            errors.append("FCBM File validation failed:")
            errors.extend(fcbm_errors)

        # Exclusions mask (required)
        self._update_progress("Validating exclusions mask", 0.07)
        exclusions_errors = raster_validator.validate_raster_file(
            self.exclusions,
            require_projected=False  # Will be validated through alignment with FCBM
        )
        if exclusions_errors:
            errors.append("Exclusions mask validation failed:")
            errors.extend(exclusions_errors)

        # Area of interest (required)
        self._update_progress("Validating area of interest", 0.08)
        aoi_errors = raster_validator.validate_raster_file(
            self.area_of_interest,
            require_projected=False  # Will be validated through alignment with FCBM
        )
        if aoi_errors:
            errors.append("Area of Interest validation failed:")
            errors.extend(aoi_errors)

        # Administrative divisions - only required for fitting/prediction stages
        # Evaluation stages do NOT use admin_divisions
        any_fitting_or_prediction = (
            self.bcm_cal or self.bcm_cnf or self.bcm_hrp or self.bcm_vp or
            self.alt_cal or self.alt_cnf or self.alt_hrp or self.alt_vp
        )
        admin_errors = []
        if any_fitting_or_prediction:
            self._update_progress("Validating administrative divisions", 0.09)
            if self._admin_divisions_is_raster:
                # Validate as raster file
                admin_errors = raster_validator.validate_raster_file(
                    self.admin_divisions,
                    require_projected=False  # Will be validated through alignment with FCBM
                )
                if admin_errors:
                    errors.append("Administrative Divisions raster validation failed:")
                    errors.extend(admin_errors)
            else:
                # Validate as vector file
                admin_errors = raster_validator.validate_vector_file(
                    self.admin_divisions,
                    require_projected=False  # Will be rasterized to match FCBM
                )
                if admin_errors:
                    errors.append("Administrative Divisions validation failed:")
                    errors.extend(admin_errors)

            # Validate CRS consistency between Administrative Divisions and FCBM
            self._update_progress("Validating CRS consistency", 0.10)
            if not fcbm_errors and not admin_errors:
                crs_consistency_errors = raster_validator.validate_crs_consistency(
                    [self.fcbm_file, self.admin_divisions]
                )
                if crs_consistency_errors:
                    if self._admin_divisions_is_raster:
                        errors.append(
                            "Administrative Divisions raster must have the same coordinate system as FCBM."
                        )
                    else:
                        errors.append(
                            "Administrative Divisions must have the same coordinate system as FCBM. "
                            "The vector_to_raster function does not reproject automatically."
                        )
                    errors.extend(crs_consistency_errors)

            # If admin_divisions is a raster, also validate alignment (extent, resolution) with FCBM
            if self._admin_divisions_is_raster and not fcbm_errors and not admin_errors:
                admin_alignment_errors = raster_validator.validate_raster_alignment(
                    [self.fcbm_file, self.admin_divisions]
                )
                if admin_alignment_errors:
                    errors.append(
                        "Administrative Divisions raster must have the same extent, resolution, "
                        "and coordinate system as FCBM."
                    )
                    errors.extend(admin_alignment_errors)

        # Validate alternative model ETP inputs based on selected stages
        # ALT CAL/CNF stages require CAL and CNF ETP images
        alt_cal_stages = self.alt_cal or self.alt_eval_cal
        alt_cnf_stages = self.alt_cnf or self.alt_eval_cnf
        alt_fitting_stages = alt_cal_stages or alt_cnf_stages
        # ALT HRP/VP stages require HRP and VP ETP images
        alt_prediction_stages = self.alt_hrp or self.alt_vp

        # ALT CAL stage requires CAL ETP image
        if alt_cal_stages:
            self._update_progress("Validating alternative ETP images (CAL)", 0.11)
            cal_etp_errors = raster_validator.validate_raster_file(
                self.alt_etp_cal_image,
                require_projected=False  # Will be validated through alignment with FCBM
            )
            if cal_etp_errors:
                errors.append(
                    "ALT Calibration (CAL) or ALT Evaluation CAL requires CAL ETP Image. "
                    "CAL ETP Image validation failed:"
                )
                errors.extend(cal_etp_errors)

        # ALT CNF stage requires CNF ETP image
        if alt_cnf_stages:
            self._update_progress("Validating alternative ETP images (CNF)", 0.115)
            cnf_etp_errors = raster_validator.validate_raster_file(
                self.alt_etp_cnf_image,
                require_projected=False  # Will be validated through alignment with FCBM
            )
            if cnf_etp_errors:
                errors.append(
                    "ALT Confirmation (CNF) or ALT Evaluation CNF requires CNF ETP Image. "
                    "CNF ETP Image validation failed:"
                )
                errors.extend(cnf_etp_errors)

        # ALT HRP stage requires HRP ETP image
        if self.alt_hrp:
            self._update_progress("Validating alternative ETP images (HRP)", 0.12)
            hrp_etp_errors = raster_validator.validate_raster_file(
                self.alt_etp_hrp_image,
                require_projected=False  # Will be validated through alignment with FCBM
            )
            if hrp_etp_errors:
                errors.append(
                    "ALT Historical Reference (HRP) requires HRP ETP Image. "
                    "HRP ETP Image validation failed:"
                )
                errors.extend(hrp_etp_errors)

        # ALT VP stage requires VP ETP image
        if self.alt_vp:
            self._update_progress("Validating alternative ETP images (VP)", 0.125)
            vp_etp_errors = raster_validator.validate_raster_file(
                self.alt_etp_vp_image,
                require_projected=False  # Will be validated through alignment with FCBM
            )
            if vp_etp_errors:
                errors.append(
                    "ALT Validity Period (VP) requires VP ETP Image. "
                    "VP ETP Image validation failed:"
                )
                errors.extend(vp_etp_errors)

        # Validate output folder
        # Note: Output folder doesn't need to exist (will be created)
        # Only validate if it exists that it's writable
        if self.output_vt7_folder:
            if os.path.exists(self.output_vt7_folder):
                folder_errors = _FolderValidator.validate_folder(
                    self.output_vt7_folder,
                    check_readable=True,
                    check_writable=True,
                    check_empty=False  # Can have existing content
                )
                if folder_errors:
                    errors.append("Output VT7 Folder validation failed:")
                    errors.extend(folder_errors)
            else:
                # Check if parent directory exists and is writable
                parent_dir = os.path.dirname(self.output_vt7_folder)
                if parent_dir and os.path.exists(parent_dir):
                    parent_errors = _FolderValidator.validate_folder(
                        parent_dir,
                        check_readable=True,
                        check_writable=True,
                        check_empty=False
                    )
                    if parent_errors:
                        errors.append(
                            f"Cannot create Output VT7 Folder '{self.output_vt7_folder}'. "
                            f"Parent directory validation failed:"
                        )
                        errors.extend(parent_errors)
                elif parent_dir and not os.path.exists(parent_dir):
                    errors.append(
                        f"Cannot create Output VT7 Folder '{self.output_vt7_folder}'. "
                        f"Parent directory does not exist: '{parent_dir}'"
                    )
        else:
            errors.append("Output VT7 Folder cannot be empty")

        # Validate spatial alignment (extent, resolution, CRS) of all input rasters
        # Collect all required rasters for alignment check
        rasters_to_check = [self.fcbm_file, self.exclusions, self.area_of_interest]

        # Add ETP rasters based on selected stages
        if alt_cal_stages and self.alt_etp_cal_image:
            rasters_to_check.append(self.alt_etp_cal_image)
        if alt_cnf_stages and self.alt_etp_cnf_image:
            rasters_to_check.append(self.alt_etp_cnf_image)
        if self.alt_hrp and self.alt_etp_hrp_image:
            rasters_to_check.append(self.alt_etp_hrp_image)
        if self.alt_vp and self.alt_etp_vp_image:
            rasters_to_check.append(self.alt_etp_vp_image)

        # Remove None values and duplicates
        rasters_to_check = [r for r in rasters_to_check if r]
        rasters_to_check = list(set(rasters_to_check))

        # Check raster alignment (extent, resolution, CRS)
        if len(rasters_to_check) >= 2:
            alignment_errors = raster_validator.validate_raster_alignment(rasters_to_check)
            if alignment_errors:
                errors.append(
                    "All input rasters must have the same extent, resolution, and coordinate system. "
                    "Please ensure all raster inputs are aligned before running VT7 workflow."
                )
                errors.extend(alignment_errors)

        # Validate at least one workflow stage is selected
        any_stage_selected = (
            self.bcm_cal or self.bcm_cnf or self.bcm_eval_cal or self.bcm_eval_cnf or
            self.bcm_hrp or self.bcm_vp or
            self.alt_cal or self.alt_cnf or self.alt_eval_cal or self.alt_eval_cnf or
            self.alt_hrp or self.alt_vp
        )

        if not any_stage_selected:
            errors.append(
                "At least one workflow stage must be selected. "
                "Please select one or more stages to execute."
            )

        # Validate Evaluation Grid Area only if evaluation stages are selected
        any_evaluation_selected = (
            self.bcm_eval_cal or self.bcm_eval_cnf or
            self.alt_eval_cal or self.alt_eval_cnf
        )
        if any_evaluation_selected:
            if not isinstance(self.evaluation_grid_area, (int, float)) or self.evaluation_grid_area <= 0:
                errors.append(
                    f"Evaluation Grid Area must be a positive number when evaluation stages are selected. "
                    f"Got: {self.evaluation_grid_area} ha"
                )

        # Validate Max Iterations only if fitting or prediction stages are selected
        any_fitting_or_prediction_selected = (
            self.bcm_cal or self.bcm_cnf or self.bcm_hrp or self.bcm_vp or
            self.alt_cal or self.alt_cnf or self.alt_hrp or self.alt_vp
        )
        if any_fitting_or_prediction_selected:
            if not isinstance(self.max_iterations, int) or self.max_iterations <= 0:
                errors.append(
                    f"Max Iterations must be a positive integer when fitting or prediction stages are selected. "
                    f"Got: {self.max_iterations}"
                )

        # Validate Expected Deforestation and VP Length only if VP (Validity Period) stages are selected
        any_vp_selected = self.bcm_vp or self.alt_vp
        if any_vp_selected:
            if self.expected_deforestation is None or self.expected_deforestation <= 0:
                errors.append(
                    f"Expected Deforestation must be a positive value when Validity Period (VP) stages are selected. "
                    f"Got: {self.expected_deforestation} ha"
                )
            if self.vp_years is None or self.vp_years <= 0:
                errors.append(
                    f"VP Length (years) must be a positive integer > 0 when Validity Period (VP) stages are selected. "
                    f"Got: {self.vp_years}"
                )

        # Validate workflow stage dependencies - check for required files from previous stages

        # Granular stage dependency validation
        # BCM CNF requires BCM CAL outputs
        if self.bcm_cnf and not self.bcm_cal:
            testing_bcm_fitting = os.path.join(
                self.output_vt7_folder, '1_Testing Stage', '1_Benchmark Model', '1_Fitting Phase (CAL)'
            )
            if not os.path.exists(testing_bcm_fitting):
                errors.append(
                    "BCM Confirmation (CNF) requires BCM Calibration (CAL) outputs. "
                    "Folder not found: '1_Testing Stage/1_Benchmark Model/1_Fitting Phase (CAL)'. "
                    "Run BCM Calibration (CAL) first or select it in this run."
                )

        # BCM Evaluation CAL requires BCM CAL outputs
        if self.bcm_eval_cal and not self.bcm_cal:
            testing_bcm_fitting = os.path.join(
                self.output_vt7_folder, '1_Testing Stage', '1_Benchmark Model', '1_Fitting Phase (CAL)'
            )
            if not os.path.exists(testing_bcm_fitting):
                errors.append(
                    "BCM Evaluation CAL requires BCM Calibration (CAL) outputs. "
                    "Folder not found: '1_Testing Stage/1_Benchmark Model/1_Fitting Phase (CAL)'. "
                    "Run BCM Calibration (CAL) first or select it in this run."
                )

        # BCM Evaluation CNF requires BCM CNF outputs
        if self.bcm_eval_cnf and not self.bcm_cnf:
            testing_bcm_prediction = os.path.join(
                self.output_vt7_folder, '1_Testing Stage', '1_Benchmark Model', '2_Prediction Phase (CNF)'
            )
            if not os.path.exists(testing_bcm_prediction):
                errors.append(
                    "BCM Evaluation CNF requires BCM Confirmation (CNF) outputs. "
                    "Folder not found: '1_Testing Stage/1_Benchmark Model/2_Prediction Phase (CNF)'. "
                    "Run BCM Confirmation (CNF) first or select it in this run."
                )

        # BCM HRP/VP require BCM CAL outputs (for NRT value)
        if (self.bcm_hrp or self.bcm_vp) and not self.bcm_cal:
            testing_bcm_fitting = os.path.join(
                self.output_vt7_folder, '1_Testing Stage', '1_Benchmark Model', '1_Fitting Phase (CAL)'
            )
            nrt_file = os.path.join(testing_bcm_fitting, build_filename("03_BCM_NRT_value.txt", self.project_name, self.version))
            if not os.path.exists(nrt_file):
                errors.append(
                    "BCM Application Stage (HRP/VP) requires NRT value from BCM Calibration (CAL). "
                    f"NRT file not found: '{os.path.basename(nrt_file)}'. "
                    "Run BCM Calibration (CAL) first or select it in this run."
                )

        # BCM VP requires BCM HRP outputs
        if self.bcm_vp and not self.bcm_hrp:
            application_bcm_fitting = os.path.join(
                self.output_vt7_folder, '2_Application Stage', '1_Benchmark Model', '1_Fitting Phase (HRP)'
            )
            if not os.path.exists(application_bcm_fitting):
                errors.append(
                    "BCM Validity Period (VP) requires BCM Historical Reference (HRP) outputs. "
                    "Folder not found: '2_Application Stage/1_Benchmark Model/1_Fitting Phase (HRP)'. "
                    "Run BCM Historical Reference (HRP) first or select it in this run."
                )

        # ALT CNF requires ALT CAL outputs
        if self.alt_cnf and not self.alt_cal:
            testing_alt_fitting = os.path.join(
                self.output_vt7_folder, '1_Testing Stage', '2_Alternative Model', '1_Fitting Phase (CAL)'
            )
            if not os.path.exists(testing_alt_fitting):
                errors.append(
                    "ALT Confirmation (CNF) requires ALT Calibration (CAL) outputs. "
                    "Folder not found: '1_Testing Stage/2_Alternative Model/1_Fitting Phase (CAL)'. "
                    "Run ALT Calibration (CAL) first or select it in this run."
                )

        # ALT Evaluation CAL requires ALT CAL outputs
        if self.alt_eval_cal and not self.alt_cal:
            testing_alt_fitting = os.path.join(
                self.output_vt7_folder, '1_Testing Stage', '2_Alternative Model', '1_Fitting Phase (CAL)'
            )
            if not os.path.exists(testing_alt_fitting):
                errors.append(
                    "ALT Evaluation CAL requires ALT Calibration (CAL) outputs. "
                    "Folder not found: '1_Testing Stage/2_Alternative Model/1_Fitting Phase (CAL)'. "
                    "Run ALT Calibration (CAL) first or select it in this run."
                )

        # ALT Evaluation CNF requires ALT CNF outputs
        if self.alt_eval_cnf and not self.alt_cnf:
            testing_alt_prediction = os.path.join(
                self.output_vt7_folder, '1_Testing Stage', '2_Alternative Model', '2_Prediction Phase (CNF)'
            )
            if not os.path.exists(testing_alt_prediction):
                errors.append(
                    "ALT Evaluation CNF requires ALT Confirmation (CNF) outputs. "
                    "Folder not found: '1_Testing Stage/2_Alternative Model/2_Prediction Phase (CNF)'. "
                    "Run ALT Confirmation (CNF) first or select it in this run."
                )

        # ALT VP requires ALT HRP outputs
        if self.alt_vp and not self.alt_hrp:
            application_alt_fitting = os.path.join(
                self.output_vt7_folder, '2_Application Stage', '2_Alternative Model', '1_Fitting Phase (HRP)'
            )
            if not os.path.exists(application_alt_fitting):
                errors.append(
                    "ALT Validity Period (VP) requires ALT Historical Reference (HRP) outputs. "
                    "Folder not found: '2_Application Stage/2_Alternative Model/1_Fitting Phase (HRP)'. "
                    "Run ALT Historical Reference (HRP) first or select it in this run."
                )

        # Check for output files that will be overwritten
        self._update_progress("Checking for existing output files", 0.14)
        existing_files_by_stage = self._get_existing_output_files_grouped(build_filename)
        if existing_files_by_stage:
            # Format message grouped by stage/folder
            grouped_messages = []
            all_file_paths = []
            for stage_name, file_paths in existing_files_by_stage.items():
                if file_paths:
                    all_file_paths.extend(file_paths)
                    # Create grouped message: stage name + list of filenames
                    filenames = [os.path.basename(fp) for fp in file_paths]
                    stage_msg = f"{stage_name}:\n  - " + "\n  - ".join(filenames)
                    grouped_messages.append(stage_msg)

            if grouped_messages:
                # Show single dialog with all grouped messages
                header = "The following output files already exist and will be overwritten:"
                full_message = header + "\n\n" + "\n\n".join(grouped_messages)
                response = _ask_yes_no_messagebox(full_message)
                if not response:  # False means "No" was clicked - add to errors to prevent operation
                    errors.append("Operation cancelled: User chose not to overwrite existing files.")

        return errors

    def _get_existing_output_files_grouped(self, build_filename) -> Dict[str, List[str]]:
        """
        Get existing output files grouped by workflow stage.

        Returns
        -------
        Dict[str, List[str]]
            Dictionary with stage names as keys and lists of existing file paths as values.
        """
        existing_files = {}

        def check_files(stage_name: str, folder: str, files: List[str]):
            """Helper to check files and add to dictionary if they exist."""
            found = []
            for filename in files:
                actual_filename = build_filename(filename, self.project_name, self.version)
                file_path = os.path.join(folder, actual_filename)
                if os.path.exists(file_path):
                    found.append(file_path)
            if found:
                existing_files[stage_name] = found

        # BCM CAL
        if self.bcm_cal:
            check_files(
                "BCM Calibration (CAL)",
                os.path.join(self.output_vt7_folder, '1_Testing Stage', '1_Benchmark Model', '1_Fitting Phase (CAL)'),
                ['01_BCM_Histogram_deforestation_distance.png', '02_BCM_Cumulative_histogram_deforestation_distance.png',
                 '03_BCM_NRT_value.txt', '04_BCM_Vulnerability_CAL.tif', '05_BCM_Modeling_Regions_CAL.tif',
                 '06_BCM_Relative_Frequency_Map_CAL.tif', '06_BCM_Relative_Frequency_Table_CAL.xlsx',
                 '07_BCM_Fitting_Density_Map_CAL.tif']
            )

        # BCM CNF
        if self.bcm_cnf:
            check_files(
                "BCM Confirmation (CNF)",
                os.path.join(self.output_vt7_folder, '1_Testing Stage', '1_Benchmark Model', '2_Prediction Phase (CNF)'),
                ['01_BCM_Vulnerability_CNF.tif', '02_BCM_Modeling_Regions_CNF.tif',
                 '03_BCM_Prediction_Density_Map_CNF.tif', '04_BCM_Adjusted_Prediction_Density_Map_CNF.tif',
                 '05_BCM_AR_log_CNF.txt']
            )

        # BCM Evaluation CAL
        if self.bcm_eval_cal:
            check_files(
                "BCM Evaluation CAL",
                os.path.join(self.output_vt7_folder, '1_Testing Stage', '1_Benchmark Model', '3_Model Evaluation'),
                ['01_BCM_Fitting_Phase_Evaluation.png', '01_BCM_Fitting_Phase_Evaluation_statistics.txt',
                 '01_BCM_Fitting_Phase_Evaluation_residuals.shp', '01_BCM_Fitting_Phase_Evaluation_grid.xlsx']
            )

        # BCM Evaluation CNF
        if self.bcm_eval_cnf:
            check_files(
                "BCM Evaluation CNF",
                os.path.join(self.output_vt7_folder, '1_Testing Stage', '1_Benchmark Model', '3_Model Evaluation'),
                ['02_BCM_Prediction_Phase_Evaluation.png', '02_BCM_Prediction_Phase_Evaluation_statistics.txt',
                 '02_BCM_Prediction_Phase_Evaluation_residuals.shp', '02_BCM_Prediction_Phase_Evaluation_grid.xlsx']
            )

        # BCM HRP
        if self.bcm_hrp:
            check_files(
                "BCM Historical Reference (HRP)",
                os.path.join(self.output_vt7_folder, '2_Application Stage', '1_Benchmark Model', '1_Fitting Phase (HRP)'),
                ['01_BCM_Vulnerability_HRP.tif', '02_BCM_Modeling_Regions_HRP.tif',
                 '03_BCM_Relative_Frequency_Map_HRP.tif', '03_BCM_Relative_Frequency_Table_HRP.xlsx',
                 '04_BCM_Fitting_Density_Map_HRP.tif']
            )

        # BCM VP
        if self.bcm_vp:
            check_files(
                "BCM Validity Period (VP)",
                os.path.join(self.output_vt7_folder, '2_Application Stage', '1_Benchmark Model', '2_Prediction Phase (VP)'),
                ['01_BCM_Vulnerability_VP.tif', '02_BCM_Modeling_Regions_VP.tif',
                 '03_BCM_Prediction_Density_Map_VP.tif', '04_BCM_Adjusted_Prediction_Density_Map_VP.tif',
                 '05_BCM_AR_log_VP.txt']
            )

        # ALT CAL
        if self.alt_cal:
            check_files(
                "ALT Calibration (CAL)",
                os.path.join(self.output_vt7_folder, '1_Testing Stage', '2_Alternative Model', '1_Fitting Phase (CAL)'),
                ['01_ALT_Vulnerability_CAL.tif', '02_ALT_Modeling_Regions_CAL.tif',
                 '03_ALT_Relative_Frequency_Map_CAL.tif', '03_ALT_Relative_Frequency_Table_CAL.xlsx',
                 '04_ALT_Fitting_Density_Map_CAL.tif']
            )

        # ALT CNF
        if self.alt_cnf:
            check_files(
                "ALT Confirmation (CNF)",
                os.path.join(self.output_vt7_folder, '1_Testing Stage', '2_Alternative Model', '2_Prediction Phase (CNF)'),
                ['01_ALT_Vulnerability_CNF.tif', '02_ALT_Modeling_Regions_CNF.tif',
                 '03_ALT_Prediction_Density_Map_CNF.tif', '04_ALT_Adjusted_Prediction_Density_Map_CNF.tif',
                 '05_ALT_AR_log_CNF.txt']
            )

        # ALT Evaluation CAL
        if self.alt_eval_cal:
            check_files(
                "ALT Evaluation CAL",
                os.path.join(self.output_vt7_folder, '1_Testing Stage', '2_Alternative Model', '3_Model Evaluation'),
                ['01_ALT_Fitting_Phase_Evaluation.png', '01_ALT_Fitting_Phase_Evaluation_statistics.txt',
                 '01_ALT_Fitting_Phase_Evaluation_residuals.shp', '01_ALT_Fitting_Phase_Evaluation_grid.xlsx']
            )

        # ALT Evaluation CNF
        if self.alt_eval_cnf:
            check_files(
                "ALT Evaluation CNF",
                os.path.join(self.output_vt7_folder, '1_Testing Stage', '2_Alternative Model', '3_Model Evaluation'),
                ['02_ALT_Prediction_Phase_Evaluation.png', '02_ALT_Prediction_Phase_Evaluation_statistics.txt',
                 '02_ALT_Prediction_Phase_Evaluation_residuals.shp', '02_ALT_Prediction_Phase_Evaluation_grid.xlsx']
            )

        # ALT HRP
        if self.alt_hrp:
            check_files(
                "ALT Historical Reference (HRP)",
                os.path.join(self.output_vt7_folder, '2_Application Stage', '2_Alternative Model', '1_Fitting Phase (HRP)'),
                ['01_ALT_Vulnerability_HRP.tif', '02_ALT_Modeling_Regions_HRP.tif',
                 '03_ALT_Relative_Frequency_Map_HRP.tif', '03_ALT_Relative_Frequency_Table_HRP.xlsx',
                 '04_ALT_Fitting_Density_Map_HRP.tif']
            )

        # ALT VP
        if self.alt_vp:
            check_files(
                "ALT Validity Period (VP)",
                os.path.join(self.output_vt7_folder, '2_Application Stage', '2_Alternative Model', '2_Prediction Phase (VP)'),
                ['01_ALT_Vulnerability_VP.tif', '02_ALT_Modeling_Regions_VP.tif',
                 '03_ALT_Prediction_Density_Map_VP.tif', '04_ALT_Adjusted_Prediction_Density_Map_VP.tif',
                 '05_ALT_AR_log_VP.txt']
            )

        return existing_files

    def _process_single(self) -> str:
        """
        Process the VT7 workflow (required by BaseFileProcessor).

        Returns
        -------
        str
            Message indicating successful completion
        """
        # Call the implementation method
        self._process_implementation()

        # Return success message
        return f"VT7 UDEF_ARP workflow completed successfully. Results saved to: {self.output_vt7_folder}"

    def _process_implementation(self) -> Dict[str, Any]:
        """
        Execute the VT7 workflow with detailed progress tracking.

        Returns
        -------
        dict
            Dictionary containing workflow results
        """
        from terracover.modules.vt7.utils import build_filename
        gdal.UseExceptions()

        current_progress = 0.25

        # Check for cancellation at start
        if self._check_cancellation():
            raise RuntimeError("Operation cancelled by user")

        # Step 1: Folder structure setup
        self._update_progress("Setting up VT7 folder structure", current_progress)
        folders = VT7FolderStructure(self.output_vt7_folder)
        current_progress += 0.05

        # Step 2: Rasterize Administrative Divisions (if vector) or use existing raster
        # Only needed for fitting/prediction stages, not for evaluation-only runs
        any_fitting_or_prediction = (
            self.bcm_cal or self.bcm_cnf or self.bcm_hrp or self.bcm_vp or
            self.alt_cal or self.alt_cnf or self.alt_hrp or self.alt_vp
        )
        admin_divisions_raster = None
        if any_fitting_or_prediction:
            if self._check_cancellation():
                raise RuntimeError("Operation cancelled by user")

            if self._admin_divisions_is_raster:
                # Admin divisions is already a raster - use it directly (no copy needed)
                self._update_progress("Using administrative divisions raster", current_progress)
                admin_divisions_raster = self.admin_divisions
            else:
                # Admin divisions is a vector - rasterize it to a temporary file
                self._update_progress("Rasterizing administrative divisions", current_progress)
                temp_admin_file = tempfile.NamedTemporaryFile(suffix='_admin_divisions.tif', delete=False, dir=tempfile.gettempdir())
                self._admin_divisions_raster_temp = temp_admin_file.name
                temp_admin_file.close()
                admin_divisions_raster = self._admin_divisions_raster_temp
                admin_divisions_to_raster(
                    self.admin_divisions,
                    self.fcbm_file,
                    admin_divisions_raster,
                    data_type=gdal.GDT_Int16,
                    id_field='ID',
                    mask_file=self.fcbm_file,
                    nodata=-1,
                    compress='lzw'
                )
        current_progress += 0.03

        # Step 3.5: Create combined mask from exclusions AND area_value
        # Combines two conditions:
        # 1. exclusions == 1 → excluded (0)
        # 2. area_of_interest != area_value → excluded (0)
        # Output mask: 1 where both conditions pass (included), 0 otherwise
        self._update_progress("Creating combined mask from exclusions and area value", current_progress)

        # Create temporary file for combined mask
        temp_mask_file = tempfile.NamedTemporaryFile(suffix='_combined_mask.tif', delete=False, dir=tempfile.gettempdir())
        self._jnr_with_exclusions_mask_temp = temp_mask_file.name
        temp_mask_file.close()

        # Use raster_calculator to create combined mask
        # map1 = area_of_interest, map2 = exclusions
        # Result: 1 if (area_of_interest == area_value AND exclusions != 1), else 0
        # This is a binary mask (0/1) used for multiplication in downstream processing
        # Note: 0 is used instead of NoData because NRT calculation multiplies arrays
        raster_calculator(
            input_files=[self.area_of_interest, self.exclusions],
            output_file=self._jnr_with_exclusions_mask_temp,
            expression=f"if((map1[1] == {self.area_value}) & (map2[1] != 1), 1, 0)",
            out_dtype="uint8"
        )
        current_progress += 0.02

        # Initialize results dictionary
        results = {
            'folders': folders,
            'admin_divisions_raster': admin_divisions_raster,
            'inverted_mask_temp': self._jnr_with_exclusions_mask_temp
        }

        # Step 3: Run Benchmark Model - Testing Stage (CAL/CNF)
        if self.bcm_cal or self.bcm_cnf:
            if self._check_cancellation():
                raise RuntimeError("Operation cancelled by user")

            self._update_progress("Running Benchmark Model - Testing Stage", current_progress)
            bcm_testing = run_testing_stage(
                folders=folders,
                fcbm_file=self.fcbm_file,
                jnr_with_exclusions_mask=self._jnr_with_exclusions_mask_temp,
                admin_divisions=admin_divisions_raster,
                n_classes=30,
                max_iterations=self.max_iterations,
                project_name=self.project_name,
                version=self.version,
                run_cal=self.bcm_cal,
                run_cnf=self.bcm_cnf,
                cancel_flag=self.cancel_flag
            )
            results['bcm_testing'] = bcm_testing
            current_progress += 0.12

        # Step 4: Run Benchmark Evaluation (CAL/CNF)
        if self.bcm_eval_cal or self.bcm_eval_cnf:
            if self._check_cancellation():
                raise RuntimeError("Operation cancelled by user")

            self._update_progress("Evaluating Benchmark Model", current_progress)
            bcm_evaluation = evaluate_testing_stage(
                folders=folders,
                fcbm_file=self.fcbm_file,
                jnr_lb_full_areas=self.area_of_interest,
                jnr_with_exclusions_mask=self._jnr_with_exclusions_mask_temp,
                jnr_value=self.area_value,
                model_type='benchmark',
                evaluation_grid_area=self.evaluation_grid_area,
                evaluation_xmax="default",
                evaluation_ymax="default",
                project_name=self.project_name,
                version=self.version,
                run_eval_cal=self.bcm_eval_cal,
                run_eval_cnf=self.bcm_eval_cnf,
                cancel_flag=self.cancel_flag
            )
            results['bcm_evaluation'] = bcm_evaluation
            current_progress += 0.08

        # Step 5: Run Benchmark Model - Application Stage (HRP/VP)
        if self.bcm_hrp or self.bcm_vp:
            if self._check_cancellation():
                raise RuntimeError("Operation cancelled by user")

            self._update_progress("Running Benchmark Model - Application Stage", current_progress)
            bcm_application = run_application_stage(
                folders=folders,
                fcbm_file=self.fcbm_file,
                jnr_with_exclusions_mask=self._jnr_with_exclusions_mask_temp,
                admin_divisions=admin_divisions_raster,
                n_classes=30,
                max_iterations=self.max_iterations,
                expected_deforestation=self.expected_deforestation,
                model_type='benchmark',
                project_name=self.project_name,
                version=self.version,
                run_hrp=self.bcm_hrp,
                run_vp=self.bcm_vp,
                vp_years=self.vp_years,
                cancel_flag=self.cancel_flag
            )
            results['bcm_application'] = bcm_application
            current_progress += 0.10

        # Step 6: Run Alternative Model - Testing Stage (CAL/CNF)
        if self.alt_cal or self.alt_cnf:
            if self._check_cancellation():
                raise RuntimeError("Operation cancelled by user")

            self._update_progress("Running Alternative Model - Testing Stage", current_progress)
            alt_testing = run_testing_stage(
                folders=folders,
                fcbm_file=self.fcbm_file,
                jnr_with_exclusions_mask=self._jnr_with_exclusions_mask_temp,
                admin_divisions=admin_divisions_raster,
                n_classes=30,
                max_iterations=self.max_iterations,
                model_type='alternative',
                alt_etp_cal_image=self.alt_etp_cal_image if self.alt_cal else None,
                alt_etp_cnf_image=self.alt_etp_cnf_image if self.alt_cnf else None,
                project_name=self.project_name,
                version=self.version,
                run_cal=self.alt_cal,
                run_cnf=self.alt_cnf,
                cancel_flag=self.cancel_flag
            )
            results['alt_testing'] = alt_testing
            current_progress += 0.12

        # Step 7: Run Alternative Evaluation (CAL/CNF)
        if self.alt_eval_cal or self.alt_eval_cnf:
            if self._check_cancellation():
                raise RuntimeError("Operation cancelled by user")

            self._update_progress("Evaluating Alternative Model", current_progress)
            alt_evaluation = evaluate_testing_stage(
                folders=folders,
                fcbm_file=self.fcbm_file,
                jnr_lb_full_areas=self.area_of_interest,
                jnr_with_exclusions_mask=self._jnr_with_exclusions_mask_temp,
                jnr_value=self.area_value,
                model_type='alternative',
                evaluation_grid_area=self.evaluation_grid_area,
                evaluation_xmax="default",
                evaluation_ymax="default",
                project_name=self.project_name,
                version=self.version,
                run_eval_cal=self.alt_eval_cal,
                run_eval_cnf=self.alt_eval_cnf,
                cancel_flag=self.cancel_flag
            )
            results['alt_evaluation'] = alt_evaluation
            current_progress += 0.08

        # Step 8: Run Alternative Model - Application Stage (HRP/VP)
        if self.alt_hrp or self.alt_vp:
            if self._check_cancellation():
                raise RuntimeError("Operation cancelled by user")

            self._update_progress("Running Alternative Model - Application Stage", current_progress)
            alt_application = run_application_stage(
                folders=folders,
                fcbm_file=self.fcbm_file,
                jnr_with_exclusions_mask=self._jnr_with_exclusions_mask_temp,
                admin_divisions=admin_divisions_raster,
                n_classes=30,
                max_iterations=self.max_iterations,
                expected_deforestation=self.expected_deforestation,
                model_type='alternative',
                alt_etp_hrp_image=self.alt_etp_hrp_image if self.alt_hrp else None,
                alt_etp_vp_image=self.alt_etp_vp_image if self.alt_vp else None,
                project_name=self.project_name,
                version=self.version,
                run_hrp=self.alt_hrp,
                run_vp=self.alt_vp,
                vp_years=self.vp_years,
                cancel_flag=self.cancel_flag
            )
            results['alt_application'] = alt_application
            current_progress += 0.10

        # Step 10: Workflow completion
        # Clean up temporary files
        if self._jnr_with_exclusions_mask_temp and os.path.exists(self._jnr_with_exclusions_mask_temp):
            try:
                os.remove(self._jnr_with_exclusions_mask_temp)
            except Exception as e:
                # Non-critical error, just log it
                self._update_progress(f"Warning: Could not remove temporary mask file: {e}", 0.93)

        if self._admin_divisions_raster_temp and os.path.exists(self._admin_divisions_raster_temp):
            try:
                os.remove(self._admin_divisions_raster_temp)
            except Exception as e:
                # Non-critical error, just log it
                self._update_progress(f"Warning: Could not remove temporary admin divisions file: {e}", 0.93)
        self._update_progress("VT7 workflow completed successfully", 0.95)

        return results

    def get_expected_files(self) -> Dict[str, List[str]]:
        """
        Get expected input and output files for the workflow.

        Returns
        -------
        dict
            Dictionary with 'input' and 'output' lists of file paths
        """
        input_files = []
        output_files = []

        # Input files
        if self.fcbm_file:
            input_files.append(self.fcbm_file)
        if self.exclusions:
            input_files.append(self.exclusions)
        if self.admin_divisions:
            input_files.append(self.admin_divisions)
        if self.area_of_interest:
            input_files.append(self.area_of_interest)
        if self.alt_etp_cal_image:
            input_files.append(self.alt_etp_cal_image)
        if self.alt_etp_cnf_image:
            input_files.append(self.alt_etp_cnf_image)
        if self.alt_etp_hrp_image:
            input_files.append(self.alt_etp_hrp_image)
        if self.alt_etp_vp_image:
            input_files.append(self.alt_etp_vp_image)

        # Output folder
        if self.output_vt7_folder:
            output_files.append(self.output_vt7_folder)

        return {
            'input': input_files,
            'output': output_files
        }


# ------------------------------------------------------------------------
# Main Processing Function
# ------------------------------------------------------------------------

def udef_arp(
    fcbm_file,
    exclusions,
    admin_divisions,
    area_of_interest,
    output_vt7_folder,
    area_value=1,
    alt_etp_cal_image=None,
    alt_etp_cnf_image=None,
    alt_etp_hrp_image=None,
    alt_etp_vp_image=None,
    expected_deforestation=None,
    max_iterations=5,
    evaluation_grid_area=100000,
    vp_years=None,
    project_name=None,
    version=None,
    workflow_stages=None,
    progress_callback=None,
    cancel_flag=None,
    show_progress=True,
    validate_inputs=True
):
    """
    Execute VT0007 UDef-ARP (Unplanned Deforestation Allocated Risk Modeling and Mapping Procedure) workflow.

    This function runs the complete VT0007 vulnerability mapping analysis including:
    - On-demand VT7 map generation (forest, non-forest, deforestation, distance)
    - Benchmark model testing and application (optional)
    - Alternative model testing and application (optional)
    - Model evaluation (optional)

    Parameters
    ----------
    fcbm_file : str
        Path to the FCBM classification map (required)
    exclusions : str
        Path to exclusions mask raster (1=excluded areas, 0 or other values=included areas) (required)
    admin_divisions : str
        Path to administrative divisions file (vector or raster). Accepted formats:
        Shapefile (.shp), GeoPackage (.gpkg), or GeoTIFF (.tif/.tiff). Vector files
        will be rasterized automatically. Raster files must have the same extent,
        resolution, and CRS as the FCBM file. (required)
    area_of_interest : str
        Path to area of interest mask raster (required). This is the complete area
        WITHOUT exclusions removed. Exclusions are applied internally during processing.
        Must be an integer raster where valid regions have values > 0 (e.g., 1, 50, 100).
        Pixels with value 0 or NoData are excluded from processing.
    area_value : int, optional
        Value in area_of_interest raster that defines the specific analysis area (default: 1).
        Only pixels matching this value will be processed.
    output_vt7_folder : str
        Path to the output VT7 folder (required)
    alt_etp_cal_image : str, optional
        Path to calibration period ETP image for alternative model
    alt_etp_cnf_image : str, optional
        Path to confirmation period ETP image for alternative model
    alt_etp_hrp_image : str, optional
        Path to historical reference period ETP image for alternative model
    alt_etp_vp_image : str, optional
        Path to validation period ETP image for alternative model
    expected_deforestation : float
        Expected deforestation in validation period in ha (required for VP stages)
    max_iterations : int, optional
        Maximum number of iterations for NRT calculation (default: 5)
    evaluation_grid_area : float, optional
        Area of evaluation grid cells in ha (default: 100000)
    vp_years : int
        Length of the Validity Period in years (required). The VP output will be
        converted to annual deforestation rate (ha/year per pixel) following VT0007
        methodology. Must be a positive integer > 0.
        Example: vp_years=5 divides the adjusted density map by 5 to get annual rates.
    project_name : str, optional
        Project name to prepend to output filenames (default: None, no prefix added)
        Example: "MyProject" results in files like "MyProject_T1_forest_v1.tif"
    version : str, optional
        Version identifier to append to output filenames (default: None, no suffix added)
        Example: "1" results in files like "T1_forest_v1.tif"
    workflow_stages : list, optional
        List of workflow stages to execute. Options:
        - BCM Calibration (CAL): Benchmark model calibration phase
        - BCM Confirmation (CNF): Benchmark model confirmation phase
        - BCM Evaluation CAL: Evaluate benchmark model CAL phase
        - BCM Evaluation CNF: Evaluate benchmark model CNF phase
        - BCM Historical Reference (HRP): Benchmark model HRP phase
        - BCM Validity Period (VP): Benchmark model VP phase
        - ALT Calibration (CAL): Alternative model calibration phase
        - ALT Confirmation (CNF): Alternative model confirmation phase
        - ALT Evaluation CAL: Evaluate alternative model CAL phase
        - ALT Evaluation CNF: Evaluate alternative model CNF phase
        - ALT Historical Reference (HRP): Alternative model HRP phase
        - ALT Validity Period (VP): Alternative model VP phase
    progress_callback : callable, optional
        Callback function for progress updates. Should accept two parameters:
        message (str) and percent (float, 0.0-1.0). Example: progress_callback("Processing...", 0.5)
    cancel_flag : callable, optional
        Callback function to check for user cancellation. Should return bool:
        True to cancel, False to continue. Example: cancel_flag() -> bool
    show_progress : bool, optional
        Whether to show progress messages in console (default: True)
    validate_inputs : bool, optional
        Whether to validate input files before processing (default: True)

    Returns
    -------
    dict
        Dictionary containing workflow results and output paths
    """
    # Convert inputs using data converters
    text_converter = TextEntryConverter()

    # Convert file paths
    converted_fcbm_file = text_converter.to_string(fcbm_file, default_value=None)
    converted_exclusions = text_converter.to_string(exclusions, default_value=None)
    converted_admin_divisions = text_converter.to_string(admin_divisions, default_value=None)
    converted_area_of_interest = text_converter.to_string(area_of_interest, default_value=None)
    converted_output_vt7_folder = text_converter.to_string(output_vt7_folder, default_value=None)

    # Convert optional ETP images
    converted_alt_etp_cal_image = text_converter.to_string(alt_etp_cal_image, default_value=None)
    converted_alt_etp_cnf_image = text_converter.to_string(alt_etp_cnf_image, default_value=None)
    converted_alt_etp_hrp_image = text_converter.to_string(alt_etp_hrp_image, default_value=None)
    converted_alt_etp_vp_image = text_converter.to_string(alt_etp_vp_image, default_value=None)

    # Convert numeric parameters
    converted_area_value = text_converter.to_int(area_value, default_value=1)
    converted_expected_deforestation = text_converter.to_float(expected_deforestation, default_value=None)
    converted_max_iterations = text_converter.to_int(max_iterations, default_value=5)
    converted_evaluation_grid_area = text_converter.to_float(evaluation_grid_area, default_value=100000.0)
    converted_vp_years = text_converter.to_int(vp_years, default_value=None)

    # Convert project_name and version
    converted_project_name = text_converter.to_string(project_name, default_value=None)
    converted_version = text_converter.to_string(version, default_value=None)

    # Create processor and run
    processor = _UdefArpProcessor(
        fcbm_file=converted_fcbm_file,
        exclusions=converted_exclusions,
        admin_divisions=converted_admin_divisions,
        area_of_interest=converted_area_of_interest,
        output_vt7_folder=converted_output_vt7_folder,
        area_value=converted_area_value,
        alt_etp_cal_image=converted_alt_etp_cal_image,
        alt_etp_cnf_image=converted_alt_etp_cnf_image,
        alt_etp_hrp_image=converted_alt_etp_hrp_image,
        alt_etp_vp_image=converted_alt_etp_vp_image,
        expected_deforestation=converted_expected_deforestation,
        max_iterations=converted_max_iterations,
        evaluation_grid_area=converted_evaluation_grid_area,
        vp_years=converted_vp_years,
        project_name=converted_project_name,
        version=converted_version,
        workflow_stages=workflow_stages,
        progress_callback=progress_callback,
        cancel_flag=cancel_flag,
        show_progress=show_progress
    )
    return processor.run(show_progress=show_progress, validate_inputs=validate_inputs)


# ------------------------------------------------------------------------
# GUI Configuration Class
# ------------------------------------------------------------------------

class FuncInputs(FuncInputsBase):
    """Configuration class for the VT7 UDEF_ARP GUI interface."""

    def _set_title_and_documentation(self) -> None:
        """Set the title and documentation for the tool."""
        self.title = "VT0007 UDef-ARP"
        self.documentation = """
    Execute the complete Unplanned Deforestation Allocated Risk Modeling and Mapping Procedure (UDef-ARP)
    for forest vulnerability mapping and deforestation risk assessment.

    This tool implements the VT0007 methodology as described in VM0048 methodology documentation. It provides
    a complete workflow for generating vulnerability maps that can be used to stratify forest areas based
    on their risk of deforestation. The tool supports both benchmark (geometric classification) and
    alternative (user-defined) risk proxy models, allowing for flexible and robust vulnerability assessment.

    {{IMAGE:vt7-stage.png:700:300:Figure 1: VT0007 workflow stages overview showing the complete process from inputs generation through testing, application, and evaluation phases}}

    The VT7 workflow consists of three main phases:
    1. Testing Stage: Fit the vulnerability model using historical deforestation data
    2. Application Stage: Apply the fitted model to predict future deforestation vulnerability
    3. Evaluation Stage: Assess model performance using spatial sampling and statistical metrics

    (HD1) Input Parameters

    (HD2) Required Inputs
    - FCBM File: Forest Cover Benchmark Model (FCBM) classification raster containing forest change
      **classes. This is the primary input generated from the FCBM module.
    - Exclusions Mask: Raster where 1 = excluded areas, 0 or other values (50, 100, etc.) = included areas.
      **This mask will be automatically inverted to binary (0=excluded, 1=included) during processing.
      **All areas with value 1 will be excluded from the analysis.
    - Administrative Divisions: Vector or raster file containing administrative boundaries (e.g., jurisdictional areas,
      **buffer zones, councils, indigenous reserves). Accepts Shapefile (.shp), GeoPackage (.gpkg), or GeoTIFF (.tif/.tiff).
      **Vector files will be rasterized automatically. Raster files must have the same extent, resolution, and CRS as the FCBM file.
    - Area of Interest: Integer raster map defining the complete area of interest for analysis WITHOUT exclusions removed.
      **Exclusions are applied internally during processing. Must have integer values > 0 for valid regions (e.g., 1, 50, 100).
      **Pixels with value 0 or NoData are excluded from processing. Can contain multiple regions with different values.
    - Area Value: Integer value in the Area of Interest raster that defines which pixels to include in the analysis (default: 1).
      **Example: If Area of Interest raster has values 50, 100, 150 for different regions, setting Area Value = 100 will analyze only region 100.
      **Must be a positive integer matching one of the values in the Area of Interest raster.
    - Output VT7 Folder: Destination folder where all VT7 analysis results will be saved. The tool creates
      **a structured folder hierarchy within this location.

    (HD2) Alternative Model Inputs (Optional)
    - CAL ETP Image: Empirical Transition Potential (ETP) raster for Calibration period
      ** Required for: Alternative Testing and Alternative Evaluation
    - CNF ETP Image: Empirical Transition Potential (ETP) raster for Confirmation period
      ** Required for: Alternative Testing and Alternative Evaluation
    - HRP ETP Image: Empirical Transition Potential (ETP) raster for Historical Reference Period
      ** Required for: Alternative Application Stage ONLY
    - VP ETP Image: Empirical Transition Potential (ETP) raster for Validation Period
      ** Required for: Alternative Application Stage ONLY

    NOTE: ETP images are only required for the specific stages that use them:
    - Alternative Model Testing/Evaluation stages use CAL and CNF
    - Alternative Model Application Stage uses HRP and VP 

    (HD2) Parameters
    - Expected Deforestation: Expected deforestation in Validation Period (VP) in hectares (required for VP stages).
      **Used for adjustment ratio calculations in the application stage.
    - Max Iterations: Maximum iterations for NRT (Negligible Risk Threshold) calculation (default: 5).
      **Algorithm stops when convergence is reached or this limit is exceeded.
    - Evaluation Grid Area: Area of individual grid cells in hectares for Voronoi-based spatial sampling (default: 100000).
      **Larger values = fewer, larger cells; smaller values = more, smaller cells.
    - VP Length (years): Length of the Validity Period in years (required). The VP Adjusted Prediction
      **Density Map will be converted to annual deforestation rate (ha/year per pixel) by dividing by this value.
      **Must be a positive integer > 0. This follows VT0007 methodology.
    - Project Name: (Optional) Project identifier to prepend to all output filenames.
      **Example: "MyProject" results in files like "MyProject_T1_forest_v1.tif"
      **Leave blank for default naming without prefix.
    - Version: (Optional) Version identifier to append to all output filenames.
      **Example: "1" results in files like "T1_forest_v1.tif" or "MyProject_T1_forest_v1.tif"
      **Leave blank for default naming without version suffix.

    (HD1) Workflow Stages

    Select which workflow stages to execute. Each stage can be run independently or in combination.
    VT7 maps (forest, non-forest, deforestation, distance) are generated on-demand during processing.

    (HD2) Benchmark Testing
    Fits the benchmark model using geometric classification (distance-based risk stratification).
    Process:
    1. Calculates NRT (Negligible Risk Threshold) through iterative adjustment
    2. Performs geometric classification to create vulnerability classes
    3. Generates frequency tables and adjustment ratios
    4. Produces vulnerability map for HRP period fitted to observed deforestation

    (HD2) Benchmark Evaluation
    Evaluates benchmark model performance using Voronoi-based spatial sampling.
    Metrics calculated:
    - Spatial autocorrelation (Moran's I)
    - Performance by administrative region
    - Confusion matrix and accuracy statistics
    - Visualization plots saved to Evaluation folder

    (HD2) Benchmark Application
    Applies the fitted benchmark model to the Validation Period (VP).
    Produces vulnerability map adjusted to match expected deforestation area.

    (HD2) Alternative Testing
    Fits the alternative model using user-defined Empirical Transition Potential (ETP) maps.
    Requires all four ETP input images. Process similar to Benchmark Testing but uses
    ETP values instead of geometric distances.

    (HD2) Alternative Evaluation
    Evaluates alternative model performance. Same metrics as Benchmark Evaluation.

    (HD2) Alternative Application
    Applies the fitted alternative model to VP. Requires ETP maps.

    (HD1) Processing Behavior

    1. Creates VT7 folder structure with subdirectories for testing and application stages
    2. Validates all required inputs and parameters
    3. Executes selected workflow stages in sequence:
       *a. Benchmark Testing (if selected): Fits benchmark model with NRT calculation
       *b. Benchmark Evaluation (if selected): Evaluates benchmark model performance
       *c. Benchmark Application (if selected): Applies benchmark model to VP
       *d. Alternative Testing (if selected): Fits alternative model using ETP inputs
       *e. Alternative Evaluation (if selected): Evaluates alternative model performance
       *f. Alternative Application (if selected): Applies alternative model to VP
    4. Generates comprehensive outputs including vulnerability maps, frequency tables, and evaluation reports
    5. Returns dictionary containing paths to all generated outputs

    (HD1) Output Specifications

    The tool creates a structured folder hierarchy in the Output VT7 Folder:

    (HD2) 1_Testing Stage Folders
    - 1_Benchmark Model/ (BCM):
      ** 1_Fitting Phase (CAL)/
         *** 01_BCM_Histogram_deforestation_distance.png
         *** 02_BCM_Cumulative_histogram_deforestation_distance.png
         *** 03_BCM_NRT_value.txt
         *** 04_BCM_Vulnerability_CAL.tif: Vulnerability classes (1-30)
         *** 05_BCM_Modeling_Regions_CAL.tif: Admin regions with vulnerability
         *** 06_BCM_Relative_Frequency_Map_CAL.tif
         *** 06_BCM_Relative_Frequency_Table_CAL.xlsx
         *** 07_BCM_Fitting_Density_Map_CAL.tif
      ** 2_Prediction Phase (CNF)/
         *** 01_BCM_Vulnerability_CNF.tif
         *** 02_BCM_Modeling_Regions_CNF.tif
         *** 03_BCM_Prediction_Density_Map_CNF.tif
         *** 04_BCM_Adjusted_Prediction_Density_Map_CNF.tif
      ** 3_Model Evaluation/
         *** 01_BCM_Fitting_Phase_Evaluation.png: CAL evaluation scatter plot
         *** 01_BCM_Fitting_Phase_Evaluation_statistics.txt: CAL evaluation metrics
         *** 01_BCM_Fitting_Phase_Evaluation_residuals.shp: CAL residuals shapefile (with ID, Area_ha, ActualDef, PredDef, Residuals)
         *** 01_BCM_Fitting_Phase_Evaluation_grid.xlsx: CAL grid statistics
         *** 02_BCM_Prediction_Phase_Evaluation.png: CNF evaluation scatter plot
         *** 02_BCM_Prediction_Phase_Evaluation_statistics.txt: CNF evaluation metrics
         *** 02_BCM_Prediction_Phase_Evaluation_residuals.shp: CNF residuals shapefile (with ID, Area_ha, ActualDef, PredDef, Residuals)
         *** 02_BCM_Prediction_Phase_Evaluation_grid.xlsx: CNF grid statistics
    - 2_Alternative Model/ (ALT): Same structure with "ALT_" prefix

    NOTE: All files in Testing, Application, and Evaluation folders follow the same naming pattern:
      ** With project_name="MyProject" and version="1":
         *** 01_MyProject_BCM_Histogram_deforestation_distance_v1.png
         *** 04_MyProject_BCM_Vulnerability_CAL_v1.tif
      ** Project name is inserted AFTER the leading number (01_, 02_, etc.)
      ** Original names are used when project_name and version are not provided

    (HD2) 2_Application Stage Folders
    - 1_Benchmark Model/
      ** 1_Fitting Phase (HRP)/
         *** 01_BCM_Vulnerability_HRP.tif
         *** 02_BCM_Modeling_Regions_HRP.tif
         *** 03_BCM_Relative_Frequency_Map_HRP.tif
         *** 03_BCM_Relative_Frequency_Table_HRP.xlsx
         *** 04_BCM_Fitting_Density_Map_HRP.tif
      ** 2_Prediction Phase (VP)/
         *** 01_BCM_Vulnerability_VP.tif
         *** 02_BCM_Modeling_Regions_VP.tif
         *** 03_BCM_Prediction_Density_Map_VP.tif
         *** 04_BCM_Adjusted_Prediction_Density_Map_VP.tif
    - 2_Alternative Model/: Same structure with "ALT_" prefix

    (HD1) Parameter Considerations

    (HD2) Expected Deforestation
    - Should match the actual deforestation observed in VP
    - Used to calibrate the vulnerability map in Application Stage
    - Incorrect values will lead to over/under-prediction of deforestation area
    - Typical range: 1,000 - 100,000 ha depending on project size

    (HD2) Max Iterations
    - Controls convergence precision for NRT calculation
    - More iterations = higher precision but longer processing time
    - Typical values: 3-10 iterations
    - Default of 5 is sufficient for most cases

    (HD2) Evaluation Grid Area
    - Affects spatial sampling resolution for model evaluation
    - Larger grids (50,000+ ha) = faster evaluation, coarser spatial assessment
    - Smaller grids (10,000- ha) = slower evaluation, finer spatial assessment
    - Default of 25,000 ha balances speed and spatial detail
    - Should be adjusted based on total study area size

    (HD1) Python Usage
    (CODE)
    from terracover.modules import udef_arp

    # Run complete workflow with benchmark model only
    results = udef_arp(
        fcbm_file="path/to/FCBM.tif",
        exclusions="path/to/exclusions_mask.tif",
        admin_divisions="path/to/admin_divisions.shp",  # or "path/to/admin_divisions.tif" for raster
        area_of_interest="path/to/area_of_interest.tif",
        output_vt7_folder="path/to/VT7_outputs",
        expected_deforestation=29376,
        max_iterations=5,
        evaluation_grid_area=100000,
        workflow_stages=["BCM Calibration (CAL)", "BCM Confirmation (CNF)",
                        "BCM Evaluation CAL", "BCM Evaluation CNF",
                        "BCM Historical Reference (HRP)", "BCM Validity Period (VP)"]
    )

    # Run with alternative model
    results = udef_arp(
        fcbm_file="path/to/FCBM.tif",
        exclusions="path/to/exclusions_mask.tif",
        admin_divisions="path/to/admin_divisions.shp",
        area_of_interest="path/to/area_of_interest.tif",
        output_vt7_folder="path/to/VT7_outputs",
        alt_etp_cal_image="path/to/CAL_ETP.tif",
        alt_etp_cnf_image="path/to/CNF_ETP.tif",
        alt_etp_hrp_image="path/to/HRP_ETP.tif",
        alt_etp_vp_image="path/to/VP_ETP.tif",
        workflow_stages=["ALT Calibration (CAL)", "ALT Confirmation (CNF)",
                        "ALT Evaluation CAL", "ALT Evaluation CNF",
                        "ALT Historical Reference (HRP)", "ALT Validity Period (VP)"]
    )
    (/CODE)
        """

    def _configure_sections(self) -> None:
        """Configure the GUI sections and field definitions."""

        # Input files section
        fcbm_file = self._create_browse_file_field(
            field_name="fcbm_file",
            label_text="FCBM File",
            description="Select the FCBM (Forest Cover Benchmark Model) classification raster. This is the primary input generated from the FCBM module containing forest change classification.",
            extension=".raster",
        )

        exclusions = self._create_browse_file_field(
            field_name="exclusions",
            label_text="Exclusions Mask",
            description="Select the exclusions mask raster. Value 1 = excluded areas, 0 or other values (50, 100, etc.) = included areas. This mask will be automatically inverted to binary (0=excluded, 1=included) during processing.",
            extension=".raster",
        )

        admin_divisions = self._create_browse_file_field(
            field_name="admin_divisions",
            label_text="Administrative Divisions",
            description="Select the administrative divisions file (vector or raster). Accepted formats: Shapefile (.shp), GeoPackage (.gpkg), or GeoTIFF (.tif/.tiff). Vector files will be rasterized automatically. Raster files must have the same extent, resolution, and CRS as the FCBM file.",
            extension=".gis",
        )

        area_of_interest = self._create_browse_file_field(
            field_name="area_of_interest",
            label_text="Area of Interest",
            description="Select the raster map defining the area of interest for analysis. This is the complete area WITHOUT exclusions removed. Exclusions are applied internally during processing. Must be an integer raster where valid regions have values > 0 (e.g., 1, 50, 100). Pixels with value 0 or NoData are excluded.",
            extension=".raster",
        )

        area_value = self._create_text_entry_field(
            field_name="area_value",
            label_text="Area Value",
            default_value="",
            value_type=int,
            description="Pixel value in the area of interest raster that defines the specific analysis area. Only pixels matching this integer value will be processed. The raster may contain multiple region values, but only the specified value is analyzed.",
        )

        output_vt7_folder = self._create_save_folder_field(
            field_name="output_vt7_folder",
            label_text="Output VT7 Folder",
            description="Select the output folder where the complete VT7 analysis results will be saved. The tool will create a structured folder hierarchy within this location.",
        )

        # Alternative model ETP images section
        alt_etp_cal_image = self._create_browse_file_field(
            field_name="alt_etp_cal_image",
            label_text="CAL ETP Image",
            description="(Optional) Select the Empirical Transition Potential (ETP) raster for the Calibration (CAL) period. Required only if running alternative model stages.",
            extension=".raster",
        )

        alt_etp_cnf_image = self._create_browse_file_field(
            field_name="alt_etp_cnf_image",
            label_text="CNF ETP Image",
            description="(Optional) Select the Empirical Transition Potential (ETP) raster for the Confirmation (CNF) period. Required only if running alternative model stages.",
            extension=".raster",
        )

        alt_etp_hrp_image = self._create_browse_file_field(
            field_name="alt_etp_hrp_image",
            label_text="HRP ETP Image",
            description="(Optional) Select the Empirical Transition Potential (ETP) raster for the Historical Reference Period (HRP). Required ONLY for Alternative Application Stage.",
            extension=".raster",
        )

        alt_etp_vp_image = self._create_browse_file_field(
            field_name="alt_etp_vp_image",
            label_text="VP ETP Image",
            description="(Optional) Select the Empirical Transition Potential (ETP) raster for the Validation Period (VP). Required ONLY for Alternative Application Stage.",
            extension=".raster",
        )

        # Parameters section
        expected_deforestation = self._create_text_entry_field(
            field_name="expected_deforestation",
            label_text="Expected Deforestation (ha)",
            default_value="",
            value_type=float,
            description="Expected deforestation in the Validation Period (VP) in hectares. This value is used for adjustment ratio calculations in the application stage to calibrate the model predictions.",
        )

        max_iterations = self._create_text_entry_field(
            field_name="max_iterations",
            label_text="Max Iterations",
            default_value="5",
            value_type=int,
            description="Maximum number of iterations for the NRT (Negligible Risk Threshold) calculation. The algorithm will stop when convergence is reached or this limit is exceeded.",
        )

        evaluation_grid_area = self._create_text_entry_field(
            field_name="evaluation_grid_area",
            label_text="Evaluation Grid Area (ha)",
            default_value="100000",
            value_type=int,
            description="Area of individual grid cells (in hectares) for the evaluation grid used in Voronoi-based spatial sampling. Larger values create fewer, larger cells; smaller values create more, smaller cells.",
        )

        vp_years = self._create_text_entry_field(
            field_name="vp_years",
            label_text="VP Length (years)",
            default_value="",
            value_type=int,
            description="Length of the Validity Period in years (required). The VP Adjusted Prediction Density Map will be converted to annual deforestation rate (ha/year per pixel) by dividing by this value. Must be a positive integer > 0. Example: If VP is 5 years, set to 5.",
        )

        project_name = self._create_text_entry_field(
            field_name="project_name",
            label_text="Project Name (Optional)",
            default_value="",
            value_type=str,
            description="(Optional) Project name to prepend to all output filenames. Leave blank to use default naming without prefix. Example: 'MyProject' results in files like 'MyProject_T1_forest_v1.tif'",
        )

        version = self._create_text_entry_field(
            field_name="version",
            label_text="Version (Optional)",
            default_value="",
            value_type=str,
            description="(Optional) Version identifier to append to all output filenames. Leave blank to use default naming without version suffix. Example: '1' results in files like 'T1_forest_v1.tif' or 'MyProject_T1_forest_v1.tif' if project_name is also provided.",
        )

        # Workflow stages - grouped checkbox with hierarchical structure
        workflow_stages = self._create_grouped_checkbox_field(
            field_name="workflow_stages",
            label_text="Workflow Stages",
            structure={
                "benchmark": {
                    "label": "Benchmark Model (BCM)",
                    "groups": {
                        "Testing Stage": ["BCM Calibration (CAL)", "BCM Confirmation (CNF)", "BCM Evaluation CAL", "BCM Evaluation CNF"],
                        "Application Stage": ["BCM Historical Reference (HRP)", "BCM Validity Period (VP)"]
                    }
                },
                "alternative": {
                    "label": "Alternative Model (ALT)",
                    "groups": {
                        "Testing Stage": ["ALT Calibration (CAL)", "ALT Confirmation (CNF)", "ALT Evaluation CAL", "ALT Evaluation CNF"],
                        "Application Stage": ["ALT Historical Reference (HRP)", "ALT Validity Period (VP)"]
                    }
                }
            },
            default_value='',
            description="Select which workflow stages to execute. Benchmark Model uses geometric classification (distance-based). Alternative Model uses Empirical Transition Potential (ETP) inputs. Evaluation stages assess model performance for CAL and CNF periods separately.",
        )

        # Define sections
        self.sections = {
            "Required Inputs": [
                fcbm_file,
                exclusions,
                admin_divisions,
                area_of_interest,
                area_value
            ],
            "Output": [
                output_vt7_folder,
                project_name,
                version
            ],
            "Alternative Model ETP Inputs (Optional)": [
                alt_etp_cal_image,
                alt_etp_cnf_image,
                alt_etp_hrp_image,
                alt_etp_vp_image
            ],
            "Parameters": [
                expected_deforestation,
                max_iterations,
                evaluation_grid_area,
                vp_years
            ],
            "Workflow Stages": [
                workflow_stages
            ]
        }

        # Define which sections should be expanded by default
        self.sections_expand = {
            "Required Inputs": True,
            "Output": True,
            "Alternative Model ETP Inputs (Optional)": True,
            "Parameters": True,
            "Workflow Stages": True,
        }


# ------------------------------------------------------------------------
# Expected Files Function
# ------------------------------------------------------------------------

def get_expected_files_udef_arp(**params):
    """
    Get expected input and output files for VT7 UDEF_ARP processing.

    Uses the processor class to generate accurate file paths for spatial viewer.

    Parameters
    ----------
    **params : dict
        Processing parameters

    Returns
    -------
    dict
        Dictionary with 'input' and 'output' lists of file paths
    """
    processor = _UdefArpProcessor(**params)
    return processor.get_expected_files()


# ------------------------------------------------------------------------
# Main Execution
# ------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        from gui_src.utils.run_gui import run_with_spatial
    except ImportError:
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        from terracover.gui_src.utils.run_gui import run_with_spatial

    run_with_spatial(FuncInputs(), udef_arp, get_expected_files_udef_arp)
