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


from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union


# ------------------------------------------------------------------------


@dataclass
class FuncInputsBase(ABC):
    """
    Abstract base class for GUI configuration in TerraCover modules.
    
    This class provides a standardized interface for defining GUI input parameters,
    documentation, and field configurations across all processing modules. It ensures
    consistency in GUI layout, field definitions, and user experience while allowing
    module-specific customizations.
    
    The class follows the Template Method pattern, where the overall structure is
    defined in the base class, but specific implementations are delegated to subclasses
    through abstract methods.
    
    Key Features:
        - Standardized GUI field configuration patterns
        - Reusable helper methods for common field types
        - Consistent documentation and title formatting
        - Flexible section organization and expansion states
        - Type-safe field definitions with comprehensive validation
    
    Architecture Pattern:
        1. Subclass inherits from FuncInputsBase
        2. Implements abstract methods for module-specific configuration
        3. Uses helper methods for common field types (input_file, output_file, etc.)
        4. Customizes section expansion behavior as needed
    
    Attributes:
        title (str): Display title for the GUI window (set by subclass)
        documentation (str): Comprehensive documentation displayed in the GUI (set by subclass)
        sections (Dict[str, List[Dict]]): Configuration of GUI sections and input fields
        sections_expand (Dict[str, bool]): Default expansion state for GUI sections
    
    Example Usage:
        @dataclass
        class FuncInputs(FuncInputsBase):
            def _set_title_and_documentation(self) -> None:
                self.title = "My Module Tool"
                self.documentation = "Module documentation..."
            
            def _configure_sections(self) -> None:
                input_section = [self._create_input_file_field()]
                self.sections = {"Input": input_section}
    """
    
    # Abstract attributes that must be defined by subclasses
    title: str = field(init=False)
    documentation: str = field(init=False)
    
    # Common attributes initialized after __post_init__
    sections: Dict[str, List[Dict[str, Dict[str, Any]]]] = field(init=False)
    sections_expand: Dict[str, bool] = field(init=False)
    
    def __post_init__(self) -> None:
        """
        Initialize GUI configuration after dataclass instantiation.
        
        This method orchestrates the GUI configuration process by calling
        abstract methods in a specific order to ensure proper initialization.
        
        Execution Order:
            1. Set title and documentation (module-specific)
            2. Configure sections and input fields (module-specific)  
            3. Set section expansion states (with default behavior)
        
        Raises:
            NotImplementedError: If abstract methods are not implemented by subclass
        """
        self._set_title_and_documentation()
        self._configure_sections()
    
    @abstractmethod
    def _set_title_and_documentation(self) -> None:
        """
        Set the module title and documentation string.
        
        This method must be implemented by subclasses to define:
        - self.title: The display name for the GUI window
        - self.documentation: Comprehensive help text shown in the GUI
        
        The documentation should include:
        - Tool overview and purpose
        - Input parameter descriptions
        - Output specifications
        - Usage examples and recommendations
        - Python API examples with import statements
        
        Example:
            def _set_title_and_documentation(self) -> None:
                self.title = "Raster Rescale Tool"
                self.documentation = '''
                RASTER RESCALE TOOL
                ===================
                [detailed documentation]
                '''
        """
        pass
    
    @abstractmethod
    def _configure_sections(self) -> None:
        """
        Configure GUI sections and input field definitions.
        
        This method must be implemented by subclasses to define the complete
        GUI structure including sections, fields, and their configurations.
        Use helper methods for common field types to ensure consistency.
        
        Must set:
            self.sections: Dictionary mapping section names to lists of field configurations
        
        Field Configuration Format:
            Each field is a dictionary with this structure:
            {
                "field_name": {
                    "label_text": str,           # Display label
                    "default_value": str,        # Default value
                    "entry_type": str,           # GUI widget type
                    "required": bool,            # Whether field is mandatory
                    "dropdown_options": List,    # Options for dropdown fields
                    "extension": str,            # File extension filter
                    "value_type": type,          # Expected data type
                    "labels_list": List,         # Additional labels
                    "description": str           # Help text
                }
            }
        
        Example:
            def _configure_sections(self) -> None:
                input_fields = [self._create_input_file_field()]
                output_fields = [self._create_output_file_field()]
                
                self.sections = {
                    "Input": input_fields,
                    "Output": output_fields
                }
        """
        pass
    
    # ------------------------------------------------------------------------
    # Helper Methods for Common Field Configurations
    # ------------------------------------------------------------------------
    
    def _create_browse_file_field(self, 
                                field_name: str = "input_file",
                                label_text: str = "Input File", 
                                description: Optional[str] = None, 
                                extension: str = ".gis",
                                required: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Create standard input file field configuration.
        
        Generates a file browser field for selecting input files with consistent
        formatting and validation rules across all modules.
        
        Args:
            label_text (str): Display label for the field. Defaults to "Input File".
            description (str, optional): Help text explaining the field purpose.
                                       If None, uses a generic description.
            extension (str): File extension filter for the browser dialog.
                           Defaults to ".gis" for general spatial files.
                           Common options: ".raster", ".vector", ".gis", ".tif"
            required (bool): Whether the field is mandatory. Defaults to False.
        
        Returns:
            Dict[str, Dict[str, Any]]: Field configuration dictionary ready for GUI sections.
        
        Example:
            # Basic usage
            input_field = self._create_input_file_field()
            
            # Custom configuration
            raster_field = self._create_input_file_field(
                label_text="Input Raster (.tif)",
                description="Select a GeoTIFF raster file for processing.",
                extension=".raster",
                required=True
            )
        """
        default_description = f"Select {label_text.lower()} for processing."
        
        return {field_name: {
            "label_text": label_text,
            "default_value": "",
            "entry_type": "browse file",
            "required": required,
            "dropdown_options": None,
            "extension": extension,
            "value_type": str,
            "labels_list": None,
            "description": description or default_description
        }}
    
    def _create_browse_folder_field(self,
                                   field_name: str = "input_folder",
                                   label_text: str = "Input Folder",
                                   description: Optional[str] = None,
                                   extension: Optional[str] = None,
                                   required: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Create standard browse folder field configuration.
        
        Generates a folder browser field for selecting directories with
        consistent formatting and validation.
        
        Args:
            field_name (str): Internal field identifier used in processing.
            label_text (str): Display label for the field. Defaults to "Browse Folder".
            description (str, optional): Help text explaining the field purpose.
            extension (str, optional): File extension hint for folder contents.
            required (bool): Whether the field is mandatory. Defaults to False.
        
        Returns:
            Dict[str, Dict[str, Any]]: Field configuration dictionary for folder browsing.
        
        Example:
            folder_field = self._create_browse_folder_field(
                field_name="input_directory",
                label_text="Input Directory",
                description="Select directory containing input files.",
                extension=".xlsx"
            )
        """
        default_description = "Browse for a folder."
        
        return {field_name: {
            "label_text": label_text,
            "default_value": "",
            "entry_type": "browse folder",
            "required": required,
            "dropdown_options": None,
            "extension": extension,
            "value_type": str,
            "labels_list": None,
            "description": description or default_description
        }}

    def _create_browse_file_folder_field(self,
                                        field_name: str,
                                        label_text: str = "Browse File/Folder",
                                        description: Optional[str] = None,
                                        extension: str = ".gis",
                                        required: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Create standard browse file/folder field configuration.
        
        Generates a field that allows users to browse for either files or folders
        with consistent formatting and validation.
        
        Args:
            field_name (str): Internal field identifier used in processing.
            label_text (str): Display label for the field. Defaults to "Browse File/Folder".
            description (str, optional): Help text explaining the field purpose.
            extension (str): File extension filter. Defaults to ".gis".
            required (bool): Whether the field is mandatory. Defaults to False.
        
        Returns:
            Dict[str, Dict[str, Any]]: Field configuration dictionary for file/folder browsing.
        
        Example:
            browse_field = self._create_browse_file_folder_field(
                field_name="input_source",
                label_text="Input Source",
                description="Select a file or folder containing input data.",
                extension=".all"
            )
        """
        default_description = "Browse for a file or folder."
        
        return {field_name: {
            "label_text": label_text,
            "default_value": "",
            "entry_type": "browse file/folder",
            "required": required,
            "dropdown_options": None,
            "extension": extension,
            "value_type": str,
            "labels_list": None,
            "description": description or default_description
        }}

    def _create_save_file_field(self, 
                                 field_name: str = "output_file",
                                 label_text: str = "Output File", 
                                 description: Optional[str] = None, 
                                 extension: str = ".gis",
                                 required: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Create standard output file field configuration.
        
        Generates a file save dialog field for specifying output locations with
        consistent formatting and behavior across modules.
        
        Args:
            label_text (str): Display label for the field. Defaults to "Output File".
            description (str, optional): Help text explaining the field purpose.
            extension (str): File extension filter. Defaults to ".gis".
            required (bool): Whether the field is mandatory. Defaults to False.
        
        Returns:
            Dict[str, Dict[str, Any]]: Field configuration dictionary for output file selection.
        
        Example:
            output_field = self._create_output_file_field(
                label_text="Rescaled Output (.tif)",
                description="Specify path for the rescaled raster output.",
                extension=".raster",
                required=True
            )
        """
        default_description = f"Specify path for output file."
        
        return {field_name: {
            "label_text": label_text,
            "default_value": "",
            "entry_type": "save file",
            "required": required,
            "dropdown_options": None,
            "extension": extension,
            "value_type": str,
            "labels_list": None,
            "description": description or default_description
        }}
    
    def _create_save_folder_field(self,
                                   field_name: str = "output_folder",
                                   label_text: str = "Output Folder",
                                   description: Optional[str] = None,
                                   required: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Create standard output folder field configuration.
        
        Generates a folder browser field for batch processing outputs with
        consistent behavior across modules.
        
        Args:
            field_name (str): Internal field identifier used in processing. Defaults to "output_folder".
            label_text (str): Display label for the field. Defaults to "Output Folder".
            description (str, optional): Help text explaining the field purpose.
            required (bool): Whether the field is mandatory. Defaults to False.
        
        Returns:
            Dict[str, Dict[str, Any]]: Field configuration dictionary for folder selection.
        """
        default_description = "Select folder to save all processed files."
        
        return {field_name: {
            "label_text": label_text,
            "default_value": "",
            "entry_type": "save folder",
            "required": required,
            "dropdown_options": None,
            "extension": None,
            "value_type": str,
            "labels_list": None,
            "description": description or default_description
        }}
    
    def _create_save_file_folder_field(self,
                                      field_name: str = "output_file",
                                      label_text: str = "Save File/Folder",
                                      description: Optional[str] = None,
                                      extension: str = ".gis",
                                      required: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Create standard save file/folder field configuration.
        
        Generates a field that allows users to specify either a file or folder
        save location with consistent behavior.
        
        Args:
            field_name (str): Internal field identifier used in processing.
            label_text (str): Display label for the field. Defaults to "Save File/Folder".
            description (str, optional): Help text explaining the field purpose.
            extension (str): File extension filter. Defaults to ".gis".
            required (bool): Whether the field is mandatory. Defaults to False.
        
        Returns:
            Dict[str, Dict[str, Any]]: Field configuration dictionary for file/folder saving.
        
        Example:
            save_field = self._create_save_file_folder_field(
                field_name="output_destination",
                label_text="Output Destination",
                description="Specify file or folder for output data.",
                extension=".raster"
            )
        """
        default_description = "For single files: specify output file path. For batch processing: specify folder to save all outputs, or leave empty to save in original locations."
        
        return {field_name: {
            "label_text": label_text,
            "default_value": "",
            "entry_type": "save file/folder",
            "required": required,
            "dropdown_options": None,
            "extension": extension,
            "value_type": str,
            "labels_list": None,
            "description": description or default_description
        }}

    def _create_input_multiple_files_field(self,
                                 field_name: str = "input_files",
                                 label_text: str = "Multiple Input Files",
                                 description: Optional[str] = None,
                                 extension: str = ".gis",
                                 required: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Create standard multiple input files field configuration.
        
        Generates a multi-file browser field for batch processing with consistent
        formatting and validation rules.
        
        Args:
            field_name (str): Internal field identifier used in processing. Defaults to "input_files".
            label_text (str): Display label for the field. Defaults to "Multiple Input Files".
            description (str, optional): Help text explaining the field purpose.
            extension (str): File extension filter. Defaults to ".gis".
            required (bool): Whether the field is mandatory. Defaults to False.
        
        Returns:
            Dict[str, Dict[str, Any]]: Field configuration dictionary for multi-file selection.
        
        Example:
            files_field = self._create_input_multiple_files_field(
                field_name="raster_files",
                label_text="Raster Files (.tif)",
                description="Select multiple raster files for batch processing.",
                extension=".raster"
            )
        """
        default_description = f"Select multiple files for batch processing."
        
        return {field_name: {
            "label_text": label_text,
            "default_value": "[]",
            "entry_type": "browse multiple",
            "required": required,
            "dropdown_options": None,
            "extension": extension,
            "value_type": str,
            "labels_list": None,
            "description": description or default_description
        }}
    
    def _create_dropdown_field(self,
                              field_name: str,
                              label_text: str,
                              options: List[str],
                              default_value: Optional[str] = None,
                              description: Optional[str] = None,
                              required: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Create standard dropdown field configuration.
        
        Generates a selection dropdown with predefined options and consistent validation.
        
        Args:
            field_name (str): Internal field identifier used in processing.
            label_text (str): Display label for the dropdown.
            options (List[str]): List of selectable options.
            default_value (str, optional): Default selection. If None, uses first option.
            description (str, optional): Help text explaining the field purpose.
            required (bool): Whether the field is mandatory. Defaults to False.
        
        Returns:
            Dict[str, Dict[str, Any]]: Field configuration dictionary for dropdown.
        
        Example:
            method_field = self._create_dropdown_field(
                field_name="resampling_method",
                label_text="Resampling Method",
                options=["bilinear", "nearest", "cubic"],
                default_value="bilinear",
                description="Algorithm for pixel interpolation during processing."
            )
        """
        if not options:
            raise ValueError("Dropdown options cannot be empty")
        
        default = default_value or options[0]
        if default not in options:
            raise ValueError(f"Default value '{default}' not in options: {options}")
        
        return {field_name: {
            "label_text": label_text,
            "default_value": default,
            "entry_type": "dropdown",
            "required": required,
            "dropdown_options": options,
            "extension": None,
            "value_type": str,
            "labels_list": None,
            "description": description or f"Select {label_text.lower()} from available options."
        }}
    
    def _create_checkbox_field(self,
                              field_name: str,
                              label_text: str,
                              default_value: bool = False,
                              description: Optional[str] = None,
                              required: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Create standard checkbox field configuration.
        
        Generates a boolean checkbox field with consistent formatting and validation.
        
        Args:
            field_name (str): Internal field identifier used in processing.
            label_text (str): Display label for the checkbox.
            default_value (bool): Default checked state. Defaults to False.
            description (str, optional): Help text explaining the field purpose.
            required (bool): Whether the field is mandatory. Defaults to False.
        
        Returns:
            Dict[str, Dict[str, Any]]: Field configuration dictionary for checkbox.
        
        Example:
            validate_field = self._create_checkbox_field(
                field_name="validate_inputs",
                label_text="Enable Input Validation",
                default_value=True,
                description="Perform comprehensive validation before processing."
            )
        """
        return {field_name: {
            "label_text": label_text,
            "default_value": "1" if default_value else "0",
            "entry_type": "checkbox",
            "required": required,
            "dropdown_options": None,
            "extension": None,
            "value_type": bool,
            "labels_list": None,
            "description": description or f"Enable/disable {label_text.lower()}."
        }}
    
    def _create_text_entry_field(self,
                                field_name: str,
                                label_text: str,
                                default_value: str = "",
                                value_type: type = str,
                                description: Optional[str] = None,
                                required: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Create standard text entry field configuration.
        
        Generates a text input field with type validation and consistent formatting.
        
        Args:
            field_name (str): Internal field identifier used in processing.
            label_text (str): Display label for the text field.
            default_value (str): Default text value. Defaults to empty string.
            value_type (type): Expected data type (str, int, float). Defaults to str.
            description (str, optional): Help text explaining the field purpose.
            required (bool): Whether the field is mandatory. Defaults to False.
        
        Returns:
            Dict[str, Dict[str, Any]]: Field configuration dictionary for text entry.
        
        Example:
            threshold_field = self._create_text_entry_field(
                field_name="threshold_value",
                label_text="Threshold",
                default_value="0.5",
                value_type=float,
                description="Numeric threshold for classification (0.0-1.0)."
            )
        """
        return {field_name: {
            "label_text": label_text,
            "default_value": str(default_value),
            "entry_type": "text entry",
            "required": required,
            "dropdown_options": None,
            "extension": None,
            "value_type": value_type,
            "labels_list": None,
            "description": description or f"Enter {label_text.lower()} value."
        }}

    def _create_code_editor_field(self,
                                 field_name: str,
                                 label_text: str,
                                 default_value: str = "",
                                 value_type: type = str,
                                 description: Optional[str] = None,
                                 required: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Create code editor field configuration for multi-line Python code.

        Generates a code editor widget with syntax highlighting, line numbers,
        and auto-indentation features.

        Args:
            field_name (str): Internal field identifier used in processing.
            label_text (str): Display label for the code editor field.
            default_value (str): Default code text. Defaults to empty string.
            value_type (type): Expected data type (should be str). Defaults to str.
            description (str, optional): Help text explaining the field purpose.
            required (bool): Whether the field is mandatory. Defaults to False.

        Returns:
            Dict[str, Dict[str, Any]]: Field configuration dictionary for code editor.

        Example:
            code_field = self._create_code_editor_field(
                field_name="python_code",
                label_text="Python Code",
                default_value="# Enter code here\\n",
                description="Enter Python code to execute."
            )
        """
        return {field_name: {
            "label_text": label_text,
            "default_value": str(default_value),
            "entry_type": "code editor",
            "required": required,
            "dropdown_options": None,
            "extension": None,
            "value_type": value_type,
            "labels_list": None,
            "description": description or f"Enter {label_text.lower()} code."
        }}

    def _create_dynamic_rows_field(self,
                                  field_name: str,
                                  label_text: str = "Dynamic Rows",
                                  labels_list: Optional[List[str]] = None,
                                  default_value: str = "[]",
                                  description: Optional[str] = None,
                                  required: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Create standard dynamic rows field configuration.
        
        Generates a field for dynamic row data entry with customizable column
        labels and consistent validation.
        
        Args:
            field_name (str): Internal field identifier used in processing.
            label_text (str): Display label for the field. Defaults to "Dynamic Rows".
            labels_list (List[str], optional): Column labels for the dynamic rows.
            default_value (str): Default JSON array representation. Defaults to "[]".
            description (str, optional): Help text explaining the field purpose.
            required (bool): Whether the field is mandatory. Defaults to False.
        
        Returns:
            Dict[str, Dict[str, Any]]: Field configuration dictionary for dynamic rows.
        
        Example:
            rows_field = self._create_dynamic_rows_field(
                field_name="person_data",
                label_text="Person Information",
                labels_list=["First Name", "Last Name", "Age"],
                default_value="[['John', 'Doe', '30'], ['Jane', 'Smith', '25']]",
                description="Enter person information in tabular format."
            )
        """
        default_description = "Add and edit rows of data in tabular format."
        
        return {field_name: {
            "label_text": label_text,
            "default_value": default_value,
            "entry_type": "dynamic rows",
            "required": required,
            "dropdown_options": None,
            "extension": None,
            "value_type": str,
            "labels_list": labels_list,
            "description": description or default_description
        }}
    
    def _create_dynamic_rows_with_file_field(self,
                                            field_name: str,
                                            label_text: str = "Dynamic Rows with File",
                                            labels_list: Optional[List[str]] = None,
                                            default_value: str = "{}",
                                            description: Optional[str] = None,
                                            extension: Optional[str] = None,
                                            required: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Create standard dynamic rows with file field configuration.

        Generates a field for dynamic row data entry that includes file associations
        with customizable column labels and consistent validation.

        Args:
            field_name (str): Internal field identifier used in processing.
            label_text (str): Display label for the field. Defaults to "Dynamic Rows with File".
            labels_list (List[str], optional): Column labels for the dynamic rows.
            default_value (str): Default JSON object representation. Defaults to "{}".
            description (str, optional): Help text explaining the field purpose.
            extension (str, optional): File extension filter (e.g., ".vector", ".raster", ".gis").
            required (bool): Whether the field is mandatory. Defaults to False.

        Returns:
            Dict[str, Dict[str, Any]]: Field configuration dictionary for dynamic rows with file.

        Example:
            rows_file_field = self._create_dynamic_rows_with_file_field(
                field_name="file_parameters",
                label_text="File-specific Parameters",
                labels_list=["Buffer Distance (m)", "Threshold", "Processing Method"],
                extension=".vector",
                description="Configure file-specific processing parameters."
            )
        """
        default_description = "Add rows of data with associated file parameters."

        return {field_name: {
            "label_text": label_text,
            "default_value": default_value,
            "entry_type": "dynamic rows with file",
            "required": required,
            "dropdown_options": None,
            "extension": extension,
            "value_type": str,
            "labels_list": labels_list,
            "description": description or default_description
        }}
    
    def _create_list_entry_field(self,
                                field_name: str,
                                label_text: str = "List Entry",
                                labels_list: Optional[List[str]] = None,
                                default_value: str = "",
                                description: Optional[str] = None,
                                required: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Create standard list entry field configuration.
        
        Generates a field for entering list-based data with predefined labels
        and consistent validation.
        
        Args:
            field_name (str): Internal field identifier used in processing.
            label_text (str): Display label for the field. Defaults to "List Entry".
            labels_list (List[str], optional): Labels for list elements.
            default_value (str): Default value. Defaults to empty string.
            description (str, optional): Help text explaining the field purpose.
            required (bool): Whether the field is mandatory. Defaults to False.
        
        Returns:
            Dict[str, Dict[str, Any]]: Field configuration dictionary for list entry.
        
        Example:
            list_field = self._create_list_entry_field(
                field_name="coordinates",
                label_text="Coordinates",
                labels_list=["x", "y", "z", "w"],
                description="Enter coordinate values for spatial reference."
            )
        """
        default_description = "Enter values for list-based data."
        
        return {field_name: {
            "label_text": label_text,
            "default_value": default_value,
            "entry_type": "list entry",
            "required": required,
            "dropdown_options": None,
            "extension": None,
            "value_type": str,
            "labels_list": labels_list,
            "description": description or default_description
        }}
    
    def _create_multiple_checkbox_field(self,
                                       field_name: str,
                                       label_text: str,
                                       labels_list: List[str],
                                       default_value: str = "",
                                       description: Optional[str] = None,
                                       required: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Create standard multiple checkbox field configuration.
        
        Generates a multiple checkbox field with consistent formatting and validation.
        The field displays multiple checkboxes based on the labels_list and returns
        selected values as a JSON-formatted string.
        
        Args:
            field_name (str): Internal field identifier used in processing.
            label_text (str): Display label for the checkbox group.
            labels_list (List[str]): List of checkbox labels to display.
            default_value (str): JSON string of default selected values. Defaults to "".
            description (str, optional): Help text explaining the field purpose.
            required (bool): Whether the field is mandatory. Defaults to False.
        
        Returns:
            Dict[str, Dict[str, Any]]: Field configuration dictionary for multiple checkbox.
        
        Example:
            options_field = self._create_multiple_checkbox_field(
                field_name="processing_options",
                label_text="Processing Options",
                labels_list=["Option A", "Option B", "Option C"],
                default_value='["Option A"]',
                description="Select multiple processing options to apply."
            )
        """
        return {field_name: {
            "label_text": label_text,
            "default_value": default_value,
            "entry_type": "multiple checkbox",
            "required": required,
            "dropdown_options": None,
            "extension": None,
            "value_type": str,
            "labels_list": labels_list,
            "description": description or f"Select multiple options from {label_text.lower()}."
        }}

    def _create_grouped_checkbox_field(self,
                                       field_name: str,
                                       label_text: str,
                                       structure: Dict[str, Any],
                                       default_value: str = "",
                                       description: Optional[str] = None,
                                       required: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Create grouped checkbox field configuration with sections and groups.

        Generates a grouped checkbox field with hierarchical organization. Items are
        organized into sections (with headers) and optional groups (with sub-labels).
        Returns selected values as a JSON-formatted string.

        Args:
            field_name (str): Internal field identifier used in processing.
            label_text (str): Display label for the checkbox group.
            structure (Dict[str, Any]): Hierarchical structure defining sections and groups.
                Format: {
                    "section_key": {
                        "label": "Section Label",
                        "items": ["Item 1", "Item 2"],  # Simple items (no groups)
                    },
                    "section_key2": {
                        "label": "Section 2 Label",
                        "groups": {
                            "Group A": ["Item A1", "Item A2"],
                            "Group B": ["Item B1", "Item B2"]
                        }
                    }
                }
            default_value (str): JSON string of default selected values. Defaults to "".
            description (str, optional): Help text explaining the field purpose.
            required (bool): Whether the field is mandatory. Defaults to False.

        Returns:
            Dict[str, Dict[str, Any]]: Field configuration dictionary for grouped checkbox.

        Example:
            workflow_field = self._create_grouped_checkbox_field(
                field_name="workflow_stages",
                label_text="Workflow Stages",
                structure={
                    "benchmark": {
                        "label": "Benchmark Model",
                        "groups": {
                            "Testing Stage": ["BCM Calibration (CAL)", "BCM Confirmation (CNF)"],
                            "Application Stage": ["BCM Historical Reference (HRP)", "BCM Validity Period (VP)"]
                        }
                    }
                },
                default_value='[]',
                description="Select workflow stages to execute."
            )
        """
        return {field_name: {
            "label_text": label_text,
            "default_value": default_value,
            "entry_type": "grouped_checkbox",
            "required": required,
            "dropdown_options": None,
            "extension": None,
            "value_type": str,
            "labels_list": None,
            "structure": structure,
            "description": description or f"Select options from {label_text.lower()}."
        }}

    def _create_excel_column_selector_field(self,
                                            field_name: str,
                                            label_text: str,
                                            exclude_columns: Optional[List[str]] = None,
                                            default_value: str = "",
                                            description: Optional[str] = None,
                                            required: bool = False,
                                            show_sheet_selector: bool = True,
                                            show_file_browser: bool = True,
                                            parent_folder_field: Optional[str] = None,
                                            excel_file_field: Optional[str] = None,
                                            subfolder: str = "") -> Dict[str, Dict[str, Any]]:
        """
        Create Excel column selector field configuration.

        Generates a composite widget that combines a file browser for Excel files
        with a dynamic checkbox list showing column names from the selected file.

        Args:
            field_name (str): Internal field identifier used in processing.
            label_text (str): Display label for the field.
            exclude_columns (List[str], optional): Column names to exclude from selection.
            default_value (str): JSON string with file_path and selected_columns.
            description (str, optional): Help text explaining the field purpose.
            required (bool): Whether the field is mandatory. Defaults to False.
            show_sheet_selector (bool): If True, shows the sheet dropdown selector.
                If False, automatically uses the first sheet without showing the selector.
                Defaults to True.
            show_file_browser (bool): If True, shows the file browser section. If False, hides it
                and expects the file path to be constructed from parent_folder + subfolder + excel_file. Defaults to True.
            parent_folder_field (str, optional): Name of the field containing the parent folder path.
                Required when show_file_browser=False to construct the full file path.
            excel_file_field (str, optional): Name of the field containing the Excel filename.
                Required when show_file_browser=False to construct the full file path.
            subfolder (str, optional): Subfolder path relative to parent folder
                (e.g., "4_Input-Further_Input/1_Points"). Used to construct full path.

        Returns:
            Dict[str, Dict[str, Any]]: Field configuration dictionary for Excel column selector.

        Example:
            # Standalone mode with file browser
            data_field = self._create_excel_column_selector_field(
                field_name="data_config",
                label_text="Data File & Features",
                exclude_columns=["ID", "X", "Y"],
                description="Select Excel file and choose columns to use as features.",
                show_sheet_selector=False  # Hide sheet selector, use first sheet
            )

            # Linked mode (no file browser, linked to other fields)
            features_field = self._create_excel_column_selector_field(
                field_name="features",
                label_text="Features to Use",
                exclude_columns=["ID", "X", "Y"],
                show_file_browser=False,  # Hide file browser
                parent_folder_field="base_directory",  # Link to base directory
                excel_file_field="data_config_file",  # Link to Excel file
                subfolder="4_Input-Further_Input/1_Points",  # Subfolder path
                description="Select which columns to use as features."
            )
        """
        return {field_name: {
            "label_text": label_text,
            "default_value": default_value,
            "entry_type": "excel_column_selector",
            "required": required,
            "dropdown_options": None,
            "extension": ".excel",
            "value_type": str,
            "labels_list": exclude_columns or [],  # Used to pass exclude_columns
            "description": description or f"Select an Excel file and choose columns for {label_text.lower()}.",
            "show_sheet_selector": show_sheet_selector,
            "show_file_browser": show_file_browser,
            "parent_folder_field": parent_folder_field,
            "excel_file_field": excel_file_field,
            "subfolder": subfolder
        }}

    def _create_project_file_selector_field(self,
                                           field_name: str,
                                           label_text: str,
                                           file_extension: str = ".xlsx",
                                           subfolder: str = "",
                                           allow_multiple: bool = False,
                                           default_value: str = "",
                                           description: Optional[str] = None,
                                           required: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Create project file selector field configuration.

        Generates a composite widget that allows selecting a project folder
        and choosing file(s) from a specified subfolder with checkboxes.

        Args:
            field_name (str): Internal field identifier used in processing.
            label_text (str): Display label for the field.
            file_extension (str): File extension to filter (e.g., ".xlsx", ".txt").
            subfolder (str): Subfolder path relative to project folder (e.g., "4_Input-Further_Input/1_Points").
                If empty, searches in project root folder.
            allow_multiple (bool): If True, allows multiple file selection; if False, only one file.
            default_value (str): JSON string with project_folder and selected_files.
            description (str, optional): Help text explaining the field purpose.
            required (bool): Whether the field is mandatory. Defaults to False.

        Returns:
            Dict[str, Dict[str, Any]]: Field configuration dictionary for project file selector.

        Example:
            data_field = self._create_project_file_selector_field(
                field_name="data_config",
                label_text="Project & Data File",
                file_extension=".xlsx",
                subfolder="4_Input-Further_Input/1_Points",
                allow_multiple=False,
                description="Select project folder and choose Excel file with model data."
            )
        """
        return {field_name: {
            "label_text": label_text,
            "default_value": default_value,
            "entry_type": "project_file_selector",
            "required": required,
            "dropdown_options": None,
            "extension": None,  # Not used, but kept for compatibility
            "value_type": str,
            "file_extension": file_extension,
            "subfolder": subfolder,
            "allow_multiple": allow_multiple,
            "description": description or f"Select a project folder and choose file(s) for {label_text.lower()}."
        }}

    def _create_subfolder_file_dropdown_field(self,
                                             field_name: str,
                                             label_text: str,
                                             parent_folder_field: str,
                                             file_extension: str = ".tif",
                                             subfolder: str = "",
                                             pattern: str = "",
                                             default_value: str = "",
                                             description: Optional[str] = None,
                                             required: bool = False,
                                             auto_select_field: Optional[str] = None,
                                             read_only: bool = False,
                                             auto_select_pattern_map: Optional[Dict[str, str]] = None) -> Dict[str, Dict[str, Any]]:
        """
        Create subfolder file dropdown field configuration.

        Generates a dropdown widget that dynamically populates with files from a subfolder
        based on the value of another field (typically a base directory or project folder).
        The dropdown automatically updates when the parent folder field changes.

        Args:
            field_name (str): Internal field identifier used in processing.
            label_text (str): Display label for the field.
            parent_folder_field (str): Name of the field containing the parent folder path.
                This field will be monitored for changes to update the dropdown.
            file_extension (str): File extension to filter (e.g., ".tif", ".shp", ".xlsx"). Defaults to ".tif".
            subfolder (str): Subfolder path relative to parent folder (e.g., "4_Input-Further_Input").
                If empty, searches in parent folder root. Defaults to "".
            pattern (str): Optional substring pattern to filter filenames (case-insensitive).
                Only files containing this pattern will be shown. Defaults to "".
                Example: "class" will match "class_definition.xlsx", "my_classification.xlsx"
            default_value (str): Default filename to select. Defaults to "".
            description (str, optional): Help text explaining the field purpose.
            required (bool): Whether the field is mandatory. Defaults to False.
            auto_select_field (str, optional): Name of another field whose value will be used to automatically
                filter and select files. When the auto_select_field value changes, this field will automatically
                select the first file that contains the auto_select_field's value in its filename.
                Example: If auto_select_field="period_to_model" and period_to_model="HRP", it will select
                the first file containing "HRP" in its name. Defaults to None.
            read_only (bool): Whether the field should be read-only (not editable by user). Defaults to False.
                Typically used in conjunction with auto_select_field to prevent manual editing.
            auto_select_pattern_map (Dict[str, str], optional): Dictionary mapping auto_select_field values
                to search patterns. When set, the auto_select_field's value will be looked up in this map
                to get the actual search pattern. If the value is not in the map, the value itself is used.
                Example: {'CAL': 'Forest_Start', 'HRP': 'Forest_Start', 'CNF': 'Forest_Mid', 'VP': 'Forest_End'}
                This allows different field values to map to different file naming patterns.

        Returns:
            Dict[str, Dict[str, Any]]: Field configuration dictionary for subfolder file dropdown.

        Note:
            The parent_folder_field must be defined before this field in the GUI configuration.
            The widget will automatically connect to value_changed signals from the parent field.
            Returns only the filename (not the full path).

        Example:
            # First define the base directory field
            base_dir_field = self._create_browse_folder_field(
                field_name="base_directory",
                label_text="Base Directory"
            )

            # Then create the dropdown that depends on it
            region_mask_field = self._create_subfolder_file_dropdown_field(
                field_name="region_mask_name",
                label_text="Region Mask",
                parent_folder_field="base_directory",
                file_extension=".tif",
                subfolder="4_Input-Further_Input",
                description="Select the region mask file from the Further Input folder."
            )

            # Example with pattern filtering
            class_def_field = self._create_subfolder_file_dropdown_field(
                field_name="class_definition_file",
                label_text="Class Definition File",
                parent_folder_field="base_directory",
                file_extension=".xlsx",
                subfolder="4_Input-Further_Input",
                pattern="class",
                description="Select class definition Excel file. File must contain 'class' in its name."
            )
        """
        return {field_name: {
            "label_text": label_text,
            "default_value": default_value,
            "entry_type": "subfolder_file_dropdown",
            "required": required,
            "dropdown_options": None,
            "extension": None,  # Not used, but kept for compatibility
            "value_type": str,
            "file_extension": file_extension,
            "subfolder": subfolder,
            "pattern": pattern,
            "parent_folder_field": parent_folder_field,
            "auto_select_field": auto_select_field,
            "auto_select_pattern_map": auto_select_pattern_map,
            "read_only": read_only,
            "description": description or f"Select a file from {subfolder or 'the parent folder'}."
        }}

    def _create_excel_column_dropdown_field(self,
                                            field_name: str,
                                            label_text: str,
                                            parent_folder_field: str,
                                            excel_file_field: str,
                                            display_column: str = "classCodesFull",
                                            value_column: str = "classNumber",
                                            sheet_name: str = None,
                                            subfolder: str = "4_Input-Further_Input",
                                            default_value: str = "",
                                            description: Optional[str] = None,
                                            required: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Create Excel column dropdown field configuration.

        Generates a dropdown widget that reads an Excel file and populates options from a specific column.
        The widget maps display values (e.g., "Forest (FOR)") to actual values (e.g., 1).
        Automatically updates when the parent folder or Excel file fields change.

        Args:
            field_name (str): Internal field identifier used in processing.
            label_text (str): Display label for the field.
            parent_folder_field (str): Name of the field containing the parent folder path.
                This field will be monitored for changes to rebuild the Excel file path.
            excel_file_field (str): Name of the field containing the Excel filename.
                This field will be monitored for changes to reload the dropdown options.
            display_column (str): Column name to display in the dropdown (e.g., "classCodesFull").
                Defaults to "classCodesFull".
            value_column (str): Column name for the actual value to return (e.g., "classNumber").
                Defaults to "classNumber".
            sheet_name (str, optional): Sheet name to read from. If None, uses first sheet.
            subfolder (str): Subfolder path relative to parent folder. Defaults to "4_Input-Further_Input".
            default_value (str): Default value to select. Defaults to "".
            description (str, optional): Help text explaining the field purpose.
            required (bool): Whether the field is mandatory. Defaults to False.

        Returns:
            Dict[str, Dict[str, Any]]: Field configuration dictionary for Excel column dropdown.

        Note:
            The parent_folder_field and excel_file_field must be defined before this field in the GUI configuration.
            The widget will automatically connect to value_changed signals from both fields.
            The Excel file is expected to be in the subfolder specified (defaults to "4_Input-Further_Input").
            Returns the value from value_column (e.g., numeric ID), not the display text.

        Example:
            # First define the base directory and Excel file fields
            base_dir_field = self._create_browse_folder_field(
                field_name="base_directory",
                label_text="Base Directory"
            )

            class_def_field = self._create_subfolder_file_dropdown_field(
                field_name="class_definition_file",
                label_text="Class Definition File",
                parent_folder_field="base_directory",
                file_extension=".xlsx",
                subfolder="4_Input-Further_Input",
                pattern="class"
            )

            # Then create the dropdown that depends on both
            bar_class_field = self._create_excel_column_dropdown_field(
                field_name="intermediate_transition_class",
                label_text="Intermediate Transition Class",
                parent_folder_field="base_directory",
                excel_file_field="class_definition_file",
                display_column="classCodesFull",
                value_column="classNumber",
                description="Select the intermediate class for forest transitions. Dropdown shows class names but returns class numbers."
            )
        """
        return {field_name: {
            "label_text": label_text,
            "default_value": default_value,
            "entry_type": "excel_column_dropdown",
            "required": required,
            "dropdown_options": None,
            "extension": None,  # Not used, but kept for compatibility
            "value_type": int,  # Typically returns integer class numbers
            "parent_folder_field": parent_folder_field,
            "excel_file_field": excel_file_field,
            "display_column": display_column,
            "value_column": value_column,
            "sheet_name": sheet_name,
            "subfolder": subfolder,
            "description": description or f"Select value from '{display_column}' column in Excel file."
        }}

    def _create_folder_file_checkbox_field(self,
                                           field_name: str,
                                           label_text: str,
                                           parent_folder_field: str,
                                           file_extension: str = ".tif",
                                           subfolder: str = "",
                                           strip_extension: bool = True,
                                           pattern: str = "",
                                           default_value: str = "[]",
                                           description: Optional[str] = None,
                                           required: bool = False,
                                           parent_folder_fallback: Optional[str] = None,
                                           subfolder_fallback: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        Create folder file checkbox field configuration.

        Generates a widget that displays checkboxes for files in a specific folder.
        Updates dynamically when the parent folder path changes.

        Args:
            field_name (str): Internal field identifier used in processing.
            label_text (str): Display label for the field.
            parent_folder_field (str): Name of the field containing the parent folder path.
            file_extension (str): File extension to filter (e.g., ".tif", ".shp"). Defaults to ".tif".
            subfolder (str): Subfolder path relative to parent folder (e.g., "1_Input-Static"). Defaults to "".
            strip_extension (bool): If True, removes file extension from returned values. Defaults to True.
            pattern (str, optional): Substring pattern to filter filenames (case-insensitive). Defaults to "".
            default_value (str): JSON list of filenames to select by default. Defaults to "[]".
            description (str, optional): Help text explaining the field purpose.
            required (bool): Whether the field is mandatory. Defaults to False.
            parent_folder_fallback (str, optional): Alternative parent folder field to use if parent_folder_field is empty. Defaults to None.
            subfolder_fallback (str, optional): Subfolder to use when using parent_folder_fallback. Defaults to None.

        Returns:
            Dict[str, Dict[str, Any]]: Field configuration dictionary for folder file checkbox widget.

        Example:
            categorical_features = self._create_folder_file_checkbox_field(
                field_name="categorical_features",
                label_text="Categorical Features",
                parent_folder_field="base_directory",
                file_extension=".tif",
                subfolder="1_Input-Static",
                strip_extension=True,
                description="Select categorical features from static drivers folder. File names without extensions will be used."
            )
        """
        return {field_name: {
            "label_text": label_text,
            "default_value": default_value,
            "entry_type": "folder_file_checkbox",
            "required": required,
            "dropdown_options": None,
            "extension": None,
            "value_type": str,
            "parent_folder_field": parent_folder_field,
            "file_extension": file_extension,
            "subfolder": subfolder,
            "strip_extension": strip_extension,
            "pattern": pattern,
            "parent_folder_fallback": parent_folder_fallback,
            "subfolder_fallback": subfolder_fallback,
            "description": description or f"Select files from {subfolder or 'folder'} for {label_text.lower()}."
        }}

    def _create_excel_sheet_checkbox_field(self,
                                            field_name: str,
                                            label_text: str,
                                            base_directory_field: str,
                                            excel_file_field: str,
                                            default_value: str = "{}",
                                            description: Optional[str] = None,
                                            required: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Create a dynamic checkbox field that displays options from Excel sheet names.

        Generates a widget that displays checkboxes based on sheet names from an Excel file.
        This is useful for selecting scenarios, regions, or other options defined as sheets.

        Args:
            field_name (str): Internal field identifier used in processing.
            label_text (str): Display label for the field.
            base_directory_field (str): Name of the field containing the base directory path.
                Used to build full paths to the Excel file.
            excel_file_field (str): Name of the field containing the Excel filename.
                Used to read sheet names as checkbox options.
            default_value (str): JSON object with selected items. Defaults to "{}".
            description (str, optional): Help text explaining the field purpose.
            required (bool): Whether the field is mandatory. Defaults to False.

        Returns:
            Dict[str, Dict[str, Any]]: Field configuration dictionary for the checkbox widget.

        Example:
            scenario_selection = self._create_excel_sheet_checkbox_field(
                field_name="scenario_selection",
                label_text="Scenarios to Model",
                base_directory_field="base_directory",
                excel_file_field="rate_excel_file",
                description="Select which scenarios to model from rates file."
            )
        """
        return {field_name: {
            "label_text": label_text,
            "default_value": default_value,
            "entry_type": "dynamic_scenario_checkbox",
            "required": required,
            "dropdown_options": None,
            "extension": None,
            "value_type": str,
            "base_directory_field": base_directory_field,
            "rates_file_field": excel_file_field,
            "description": description or "Select options from Excel sheets."
        }}

    def _create_folder_structure_generator_field(self,
                                                  field_name: str,
                                                  label_text: str,
                                                  parent_folder_field: str,
                                                  structure_name: str = "TerraChange",
                                                  base_folder_name: str = "",
                                                  description: Optional[str] = None,
                                                  required: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Create folder structure generator field configuration.

        Generates a widget with a button to create a predefined folder structure.
        Updates dynamically when the parent folder path changes.

        Args:
            field_name (str): Internal field identifier used in processing.
            label_text (str): Display label for the field.
            parent_folder_field (str): Name of the field containing the parent folder path.
            structure_name (str): Name of predefined structure to create. Defaults to "TerraChange".
            base_folder_name (str): Name of base folder to create. If empty, creates directly in parent_folder. Defaults to "".
            description (str, optional): Help text explaining the field purpose.
            required (bool): Whether the field is mandatory. Defaults to False.

        Returns:
            Dict[str, Dict[str, Any]]: Field configuration dictionary for folder structure generator widget.

        Example:
            terrachange_structure = self._create_folder_structure_generator_field(
                field_name="terrachange_structure",
                label_text="TerraChange Folder Structure",
                parent_folder_field="base_directory",
                structure_name="TerraChange",
                base_folder_name="",
                description="Click to create the standard TerraChange folder structure."
            )
        """
        return {field_name: {
            "label_text": label_text,
            "default_value": "",
            "entry_type": "folder_structure_generator",
            "required": required,
            "dropdown_options": None,
            "extension": None,
            "value_type": str,
            "parent_folder_field": parent_folder_field,
            "structure_name": structure_name,
            "base_folder_name": base_folder_name,
            "description": description or f"Create {structure_name} folder structure with one click.",
            "ui_only": True  # This field is UI-only, not passed to the function
        }}

    def _create_model_folder_selector_field(self,
                                            field_name: str,
                                            label_text: str,
                                            parent_folder_field: str,
                                            metadata_target_fields: Optional[Dict[str, str]] = None,
                                            subfolder: str = "4_Input-Further_Input/2_Models",
                                            description: Optional[str] = None,
                                            required: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Create model folder selector field configuration.

        Generates a dropdown widget that lists model folders and extracts metadata from folder names.
        Automatically updates other fields based on the model folder name:
        - use_standardized_rasters: True if folder name contains "Std"
        - period_options: ["CAL", "CNF"] if folder contains "CAL", ["HRP", "VP"] if folder contains "HRP"

        Args:
            field_name (str): Internal field identifier used in processing.
            label_text (str): Display label for the field.
            parent_folder_field (str): Name of the field containing the parent folder path.
            metadata_target_fields (Dict[str, str], optional): Mapping of metadata keys to target field names.
                Example: {'use_standardized_rasters': 'use_std_field', 'period_options': 'period_field'}
            subfolder (str): Subfolder path relative to parent folder. Defaults to "4_Input-Further_Input/2_Models".
            description (str, optional): Help text explaining the field purpose.
            required (bool): Whether the field is mandatory. Defaults to False.

        Returns:
            Dict[str, Dict[str, Any]]: Field configuration dictionary for model folder selector widget.

        Example:
            model_folder = self._create_model_folder_selector_field(
                field_name="model_folder",
                label_text="Model Folder",
                parent_folder_field="base_directory",
                metadata_target_fields={
                    'use_standardized_rasters': 'use_standardized_rasters',
                    'period_options': 'period_to_model'
                },
                description="Select the model folder. The widget will auto-detect standardized rasters and period options."
            )
        """
        return {field_name: {
            "label_text": label_text,
            "default_value": "",
            "entry_type": "model_folder_selector",
            "required": required,
            "dropdown_options": None,
            "extension": None,
            "value_type": str,
            "parent_folder_field": parent_folder_field,
            "subfolder": subfolder,
            "metadata_target_fields": metadata_target_fields,
            "description": description or "Select the model folder. Metadata will be extracted from the folder name.",
            "ui_only": True  # This field is UI-only, not passed to the function
        }}

    def _create_suffix_field(self, 
                            field_name: str = "suffix",
                            default_suffix: str = "_processed",
                            description: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        Create standard suffix field configuration.
        
        Generates a text entry field for specifying output filename suffixes
        with consistent formatting and validation.
        
        Args:
            field_name (str): Internal field identifier used in processing. Defaults to "suffix".
            default_suffix (str): Default suffix value. Defaults to "_processed".
                                Leading underscore is automatically stripped for display.
            description (str, optional): Help text explaining the field purpose.
        
        Returns:
            Dict[str, Dict[str, Any]]: Field configuration dictionary for suffix entry.
        
        Example:
            suffix_field = self._create_suffix_field(
                field_name="output_suffix",
                default_suffix="_rescaled",
                description="Suffix for rescaled output filenames."
            )
        """
        clean_suffix = default_suffix.lstrip("_")
        default_description = f"Text to append to output filenames when processing multiple files (default: '{default_suffix}')."
        
        return {field_name: {
            "label_text": "Suffix",
            "default_value": clean_suffix,
            "entry_type": "text entry",
            "required": False,
            "dropdown_options": None,
            "extension": None,
            "value_type": str,
            "labels_list": None,
            "description": description or default_description
        }}
    
    def _create_version_field(self, 
                             field_name: str = "output_version",
                             description: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        Create standard output version field configuration.
        
        Generates a numeric entry field for version numbering with consistent
        formatting and validation rules.
        
        Args:
            field_name (str): Internal field identifier used in processing. Defaults to "output_version".
            description (str, optional): Help text explaining the field purpose.
        
        Returns:
            Dict[str, Dict[str, Any]]: Field configuration dictionary for version entry.
        
        Example:
            version_field = self._create_version_field(
                field_name="version_number",
                description="Version number for iterative processing (e.g., v1, v2)."
            )
        """
        default_description = "Optional version number to append to output filenames."
        
        return {field_name: {
            "label_text": "Output Version",
            "default_value": "",
            "entry_type": "text entry",
            "required": False,
            "dropdown_options": None,
            "extension": None,
            "value_type": int,
            "labels_list": None,
            "description": description or default_description
        }}
    
    def _create_multiprocessing_field(self,
                                     field_name: str = "multiprocessing",
                                     label_text: str = "Multiprocessing",
                                     default_value: bool = True,
                                     description: Optional[str] = None,
                                     required: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Create standard multiprocessing field configuration.
        
        Generates a checkbox field for enabling/disabling multiprocessing with consistent
        formatting and validation. This field is commonly used in processing modules
        to allow users to control parallel processing capabilities.
        
        Args:
            field_name (str): Internal field identifier used in processing. Defaults to "multiprocessing".
            label_text (str): Display label for the checkbox. Defaults to "Multiprocessing".
            default_value (bool): Default enabled state. Defaults to True.
            description (str, optional): Help text explaining the field purpose.
                                       If None, uses a comprehensive default description.
            required (bool): Whether the field is mandatory. Defaults to False.
        
        Returns:
            Dict[str, Dict[str, Any]]: Field configuration dictionary for multiprocessing checkbox.
        
        Example:
            multiprocessing_field = self._create_multiprocessing_field(
                field_name="enable_parallel",
                label_text="Enable Parallel Processing",
                default_value=True,
                description="Use multiple CPU cores for faster processing of large datasets."
            )
        """
        default_description = ("Enable parallel processing using multiple CPU cores for faster "
                              "conversion of large files. Splits the data into tiles and processes "
                              "them simultaneously. Recommended for files larger than 1GB.")
        
        return {field_name: {
            "label_text": label_text,
            "default_value": "1" if default_value else "0",
            "entry_type": "checkbox",
            "required": required,
            "dropdown_options": None,
            "extension": None,
            "value_type": bool,
            "labels_list": None,
            "description": description or default_description
        }}
    
    def _create_out_dtype_field(self,
                               field_name: str = "out_dtype",
                               label_text: str = "Output Data Type",
                               default_value: str = "none",
                               description: Optional[str] = None,
                               required: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Create standard output data type field configuration.
        
        Generates a dropdown field for selecting output data types with predefined
        options commonly used in raster processing operations.
        
        Args:
            field_name (str): Internal field identifier used in processing. Defaults to "out_dtype".
            label_text (str): Display label for the dropdown. Defaults to "Output Data Type".
            default_value (str): Default data type selection. Defaults to "none".
            description (str, optional): Help text explaining the field purpose.
                                       If None, uses a comprehensive default description.
            required (bool): Whether the field is mandatory. Defaults to False.
        
        Returns:
            Dict[str, Dict[str, Any]]: Field configuration dictionary for data type dropdown.
        
        Data Type Options:
            - uint8: Unsigned 8-bit integer (0-255) - ideal for classifications
            - uint16: Unsigned 16-bit integer (0-65,535) - larger integer ranges
            - int16: Signed 16-bit integer (-32,768 to 32,767) - signed integer data
            - uint32: Unsigned 32-bit integer (0-4,294,967,295) - very large integers
            - int32: Signed 32-bit integer (-2,147,483,648 to 2,147,483,647) - large signed integers
            - float32: 32-bit floating point (-3.4e+38 to 3.4e+38) - continuous values
            - float64: 64-bit floating point (-1.79e+308 to 1.79e+308) - high precision
            - none: Preserve original data type
        
        Example:
            dtype_field = self._create_out_dtype_field(
                field_name="output_datatype",
                label_text="Output Data Type",
                default_value="uint16",
                description="Select the data type for the output raster."
            )
        """
        data_type_options = ["uint8", "uint16", "int16", "uint32", "int32", "float32", "float64", "none"]
        
        default_description = ("Convert raster to specific data type. uint8 (0-255) for classifications, "
                              "uint16 for larger integer ranges, float32/float64 for continuous values. "
                              "'none' preserves original data type. See documentation for complete data type ranges.")
        
        return {field_name: {
            "label_text": label_text,
            "default_value": default_value,
            "entry_type": "dropdown",
            "required": required,
            "dropdown_options": data_type_options,
            "extension": None,
            "value_type": str,
            "labels_list": None,
            "description": description or default_description
        }}
    
    def _create_out_no_data_field(self,
                                 field_name: str = "out_no_data",
                                 label_text: str = "Output No Data Value",
                                 default_value: str = "",
                                 value_type: type = float,
                                 description: Optional[str] = None,
                                 required: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Create standard output no-data value field configuration.
        
        Generates a text entry field for specifying custom no-data values in
        raster processing operations with appropriate validation.
        
        Args:
            field_name (str): Internal field identifier used in processing. Defaults to "out_no_data".
            label_text (str): Display label for the text field. Defaults to "Output No Data Value".
            default_value (str): Default no-data value. Defaults to empty string (auto-detect).
            value_type (type): Expected data type for validation. Defaults to float.
            description (str, optional): Help text explaining the field purpose.
                                       If None, uses a comprehensive default description.
            required (bool): Whether the field is mandatory. Defaults to False.
        
        Returns:
            Dict[str, Dict[str, Any]]: Field configuration dictionary for no-data value entry.
        
        Common No-Data Values by Data Type:
            - uint8: 255 (maximum value)
            - uint16: 65535 (maximum value)
            - int16: -32768 (minimum value) or 32767 (maximum value)
            - uint32: 4294967295 (maximum value)
            - int32: -2147483648 (minimum value) or 2147483647 (maximum value)
            - float32/float64: NaN, -9999, or other conventional values
        
        Example:
            no_data_field = self._create_out_no_data_field(
                field_name="custom_no_data",
                label_text="Custom No Data Value",
                default_value="-9999",
                description="Specify a custom no-data value for the output."
            )
        """
        default_description = ("Custom no-data value for the output raster. If left empty, the system "
                              "will automatically use the maximum value for the chosen data type "
                              "(e.g., 255 for uint8, 65535 for uint16).")
        
        return {field_name: {
            "label_text": label_text,
            "default_value": default_value,
            "entry_type": "text entry",
            "required": required,
            "dropdown_options": None,
            "extension": None,
            "value_type": value_type,
            "labels_list": None,
            "description": description or default_description
        }}
    
    # ------------------------------------------------------------------------
    # Validation and Utility Methods
    # ------------------------------------------------------------------------
    
    def validate_configuration(self) -> List[str]:
        """
        Validate the GUI configuration for common issues.
        
        Performs comprehensive validation of the field configurations to catch
        common errors and ensure GUI compatibility.
        
        Returns:
            List[str]: List of validation error messages. Empty if validation passes.
        
        Validation Checks:
            - Required fields have proper configuration
            - Field names are unique within sections
            - Dropdown options are valid
            - File extensions are properly formatted
            - Value types are supported
        """
        errors = []
        
        # Check required attributes
        if not hasattr(self, 'title') or not self.title:
            errors.append("Title must be set by _set_title_and_documentation()")
        
        if not hasattr(self, 'documentation') or not self.documentation:
            errors.append("Documentation must be set by _set_title_and_documentation()")
        
        if not hasattr(self, 'sections') or not self.sections:
            errors.append("Sections must be configured by _configure_sections()")
        
        # Check for duplicate field names across all sections
        all_field_names = []
        for section_name, fields_list in self.sections.items():
            for field_dict in fields_list:
                field_names = list(field_dict.keys())
                all_field_names.extend(field_names)
        
        duplicates = set([name for name in all_field_names if all_field_names.count(name) > 1])
        if duplicates:
            errors.append(f"Duplicate field names found: {duplicates}")
        
        # Validate field configurations
        for section_name, fields_list in self.sections.items():
            for field_dict in fields_list:
                for field_name, config in field_dict.items():
                    field_errors = self._validate_field_config(field_name, config)
                    errors.extend([f"Section '{section_name}', Field '{field_name}': {err}" 
                                 for err in field_errors])
        
        return errors
    
    def _validate_field_config(self, field_name: str, config: Dict[str, Any]) -> List[str]:
        """
        Validate individual field configuration.
        
        Args:
            field_name (str): The field identifier.
            config (Dict[str, Any]): The field configuration dictionary.
        
        Returns:
            List[str]: List of validation errors for this field.
        """
        errors = []
        required_keys = [
            "label_text", "default_value", "entry_type", "required", 
            "dropdown_options", "extension", "value_type", "labels_list", "description"
        ]
        
        # Check required configuration keys
        missing_keys = [key for key in required_keys if key not in config]
        if missing_keys:
            errors.append(f"Missing configuration keys: {missing_keys}")
        
        # Validate entry types
        valid_entry_types = [
            "text entry", "code editor", "code_editor_with_console", "interactive_console", "browse file", "browse multiple", "save file", "save folder",
            "browse folder", "browse file/folder", "save file/folder",
            "dynamic rows", "dynamic rows with file",
            "list entry", "dropdown", "checkbox", "multiple checkbox"
        ]
        entry_type = config.get("entry_type")
        if entry_type not in valid_entry_types:
            errors.append(f"Invalid entry_type '{entry_type}'. Valid types: {valid_entry_types}")
        
        # Validate dropdown configurations
        if entry_type == "dropdown":
            options = config.get("dropdown_options")
            if not options or not isinstance(options, list):
                errors.append("Dropdown fields must have non-empty dropdown_options list")
            elif config.get("default_value") not in options:
                errors.append(f"Default value must be in dropdown options: {options}")
        
        # Validate value types
        valid_types = [str, int, float, bool]
        value_type = config.get("value_type")
        if value_type not in valid_types:
            errors.append(f"Invalid value_type '{value_type}'. Valid types: {valid_types}")
        
        return errors
    
    def get_field_names(self) -> List[str]:
        """
        Get all field names defined in the configuration.
        
        Returns:
            List[str]: List of all field identifiers across all sections.
        
        Example:
            field_names = func_inputs.get_field_names()
            # ['input_file', 'output_file', 'suffix', 'custom_param']
        """
        field_names = []
        for fields_list in self.sections.values():
            for field_dict in fields_list:
                field_names.extend(field_dict.keys())
        return field_names
    
    def get_section_names(self) -> List[str]:
        """
        Get all section names defined in the configuration.
        
        Returns:
            List[str]: List of all section names.
        """
        return list(self.sections.keys())


# ------------------------------------------------------------------------


def validate_func_inputs(func_inputs: FuncInputsBase) -> None:
    """
    Validate a FuncInputs configuration and raise errors if invalid.
    
    This utility function provides a convenient way to validate configurations
    during development and catch issues early in the development process.
    
    Args:
        func_inputs (FuncInputsBase): The configuration instance to validate.
    
    Raises:
        ValueError: If validation errors are found, with detailed error messages.
    
    Example:
        # During development/testing
        inputs = MyModuleFuncInputs()
        validate_func_inputs(inputs)  # Raises ValueError if invalid
    """
    errors = func_inputs.validate_configuration()
    if errors:
        error_msg = "GUI configuration validation failed:\n" + "\n".join(f"- {err}" for err in errors)
        raise ValueError(error_msg)


# ------------------------------------------------------------------------