# coding=utf-8
# ------------------------------------------------------------------------
#
#   Copyright:          © Terra Global Capital. All rights reserved.
#   Author:             david.montoya@terraglobalcapital.com
#   Python version:     3.11
#   GDAL version:       3.10.3
#   GeoPandas version:  1.1.1
#   PyQt6 version:      6.7.1
#   Year:               2025
#
#   VT0007 UDef-ARP Standalone Version
#   Simplified run_gui without spatial viewer support
#
#   This code is proprietary and confidential.
#   Unauthorized copying or distribution is prohibited.
#
# ------------------------------------------------------------------------


try:
    # Try relative import first (when run as module)
    from gui_src.core.create_app import create_application
except ImportError:
    # Fallback to absolute import (when run as script)
    from terracover.gui_src.core.create_app import create_application


def assess_num_columns(sections):
    """
    Assess if sections has entry_type set as 'save file/folder' or 'browse file/folder'
    Returns 4 if at least one of those options is present, else returns 3
    """
    target_entry_types = {"save file/folder", "browse file/folder"}

    for section_name, section_inputs in sections.items():
        for input_dict in section_inputs:
            for param_name, param_config in input_dict.items():
                entry_type = param_config.get("entry_type", "")
                if entry_type in target_entry_types:
                    return 4

    return 3


def run_gui(func_inputs=None, process_function=None):
    """
    Launch the GUI application.

    Args:
        func_inputs (FuncInputs): Configuration object for GUI.
        process_function (callable): Function to execute when GUI runs.
    """

    num_columns = assess_num_columns(func_inputs.sections)

    # Create and run application (without spatial viewer)
    create_application(
        func_inputs.title,
        func_inputs.documentation,
        func_inputs.sections,
        process_function,
        section_defaults=func_inputs.sections_expand,
        num_columns=num_columns,
        include_spatial_viewer=False
    )


def run_with_spatial(func_inputs=None, process_function=None, expected_files_function=None):
    """
    Launch the GUI application (standalone version without spatial viewer).

    This is an alias for run_gui in the standalone version since spatial viewer
    is not available. The expected_files_function parameter is ignored.

    Args:
        func_inputs (FuncInputs): Configuration object for GUI.
        process_function (callable): Function to execute when GUI runs.
        expected_files_function (callable): Ignored in standalone version.
    """
    run_gui(func_inputs, process_function)
