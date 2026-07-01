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
#   This code is proprietary and confidential.
#   Unauthorized copying or distribution is prohibited.
#
# ------------------------------------------------------------------------

from typing import Any, List, Optional
from dataclasses import dataclass

@dataclass
class FieldConfig:
    """Configuration for a single form field"""
    label_text: str
    entry_type: str
    required: bool = False
    default_value: str = ""
    dropdown_options: Optional[List[Any]] = None
    extension: Optional[str] = None
    value_type: type = str
    num_element_list: Optional[int] = None
    labels_list: Optional[List[str]] = None
    description: Optional[str] = None
    show_sheet_selector: bool = True  # For ExcelColumnSelector: show/hide sheet dropdown
    show_file_browser: bool = True  # For ExcelColumnSelector: show/hide file browser section
    file_extension: Optional[str] = None  # For ProjectFileSelector/SubfolderFileDropdown: file extension to filter
    subfolder: Optional[str] = None  # For ProjectFileSelector/SubfolderFileDropdown/ExcelColumnSelector: subfolder relative to project root
    allow_multiple: bool = False  # For ProjectFileSelector: allow multiple file selection
    parent_folder_field: Optional[str] = None  # For SubfolderFileDropdown/ExcelColumnDropdown/ExcelColumnSelector/FolderStructureGenerator: name of field containing parent folder path
    pattern: Optional[str] = None  # For SubfolderFileDropdown: substring pattern to filter filenames (case-insensitive)
    auto_select_field: Optional[str] = None  # For SubfolderFileDropdown: name of field whose value will be used to auto-select files
    auto_select_pattern_map: Optional[dict] = None  # For SubfolderFileDropdown: dict mapping field values to search patterns (e.g., {'CAL': 'Forest_Start', 'HRP': 'Forest_Start'})
    read_only: bool = False  # For SubfolderFileDropdown: whether the dropdown should be read-only
    display_column: Optional[str] = None  # For ExcelColumnDropdown: column name to display in dropdown
    value_column: Optional[str] = None  # For ExcelColumnDropdown: column name for actual value
    sheet_name: Optional[str] = None  # For ExcelColumnDropdown: sheet name to read from
    excel_file_field: Optional[str] = None  # For ExcelColumnDropdown/ExcelColumnSelector: name of field containing Excel filename
    strip_extension: bool = True  # For FolderFileCheckbox: whether to remove file extension from returned values
    parent_folder_fallback: Optional[str] = None  # For FolderFileCheckbox: alternative parent folder field to use if parent_folder_field is empty
    subfolder_fallback: Optional[str] = None  # For FolderFileCheckbox: subfolder to use when using parent_folder_fallback
    structure_name: Optional[str] = None  # For FolderStructureGenerator: name of predefined folder structure to create
    base_folder_name: Optional[str] = None  # For FolderStructureGenerator: name of base folder to create
    metadata_target_fields: Optional[dict] = None  # For ModelFolderSelector: dict mapping metadata keys to field names (e.g., {'use_standardized_rasters': 'use_std_field', 'period_options': 'period_field'})
    ui_only: bool = False  # If True, this field is excluded from function parameters (e.g., FolderStructureGenerator, ModelFolderSelector)
    rates_file_field: Optional[str] = None  # For DynamicScenarioCheckbox: name of field containing rates Excel filename
    base_directory_field: Optional[str] = None  # For DynamicScenarioCheckbox: name of field containing base directory path
    structure: Optional[dict] = None  # For GroupedCheckbox: hierarchical structure dict with sections and groups