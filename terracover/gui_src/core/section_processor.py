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


"""
Section processor for organizing form fields into collapsible sections
PyQt6 implementation with dark theme styling
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                             QGroupBox, QScrollArea, QFrame, QLabel, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal
from typing import Dict, List
import json
import logging
from datetime import datetime

try:
    from .dialog_theming import show_question_dialog
except ImportError:
    from terracover.gui_src.core.dialog_theming import show_question_dialog

logger = logging.getLogger(__name__)

try:
    from ..utils.json_formatter import ConfigJsonFormatter
except ImportError:
    # Fallback if formatter is not available
    ConfigJsonFormatter = None

from .field_config import FieldConfig
from ..widgets.widget_factory import WidgetFactory


class CollapsibleGroupBox(QGroupBox):
    """A collapsible group box widget"""

    toggled = pyqtSignal(bool)

    def __init__(self, title: str = "", parent=None):
        super().__init__(title, parent)
        self.setCheckable(True)
        self.setChecked(True)  # Expanded by default
        self.clicked.connect(self._on_clicked)

        # Store original content widget
        self.content_widget = None

    def setContentWidget(self, widget):
        """Set the content widget"""
        if self.content_widget:
            self.content_widget.setParent(None)

        self.content_widget = widget

        # Create layout if needed
        if not self.layout():
            layout = QVBoxLayout(self)
            layout.setContentsMargins(10, 20, 10, 10)

        self.layout().addWidget(widget)
        self._update_visibility()

    def _on_clicked(self, checked):
        """Handle group box toggle"""
        self._update_visibility()
        self.toggled.emit(checked)

    def _update_visibility(self):
        """Update content visibility based on checked state"""
        if self.content_widget:
            self.content_widget.setVisible(self.isChecked())


class HiddenWidget(QWidget):
    """A hidden widget for storing values without displaying in the GUI"""
    value_changed = pyqtSignal()

    def __init__(self, default_value="", parent=None):
        super().__init__(parent)
        self._value = default_value

    def get_value(self):
        return self._value

    def set_value(self, v):
        self._value = str(v)


class SectionProcessor(QWidget):
    """Processes sections and creates GUI elements"""
    
    values_changed = pyqtSignal()
    
    def __init__(self, sections: Dict[str, List[Dict]], parent=None, 
                 section_defaults: Dict[str, bool] = None, module_title: str = None):
        super().__init__(parent)
        self.sections = sections
        self.section_defaults = section_defaults or {}
        self.module_title = module_title or "Unknown Module"
        self.field_widgets = {}  # Store widgets by parameter name
        self.field_configs = {}  # Store configurations by parameter name
        
        # Set up main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
    def create_gui_elements(self, parent_widget=None, starting_row: int = 0):
        """Create GUI elements for all sections"""
        current_row = starting_row
        
        # If no parent_widget is provided or parent_widget is self, use self
        if parent_widget is None or parent_widget is self:
            target_layout = self.main_layout
        else:
            # Use parent widget's layout
            if hasattr(parent_widget, 'layout') and parent_widget.layout():
                target_layout = parent_widget.layout()
            else:
                # Create layout for parent if needed
                if not parent_widget.layout():
                    layout = QVBoxLayout(parent_widget)
                    parent_widget.setLayout(layout)
                target_layout = parent_widget.layout()
        
        for section_name, section_inputs in self.sections.items():
            # Skip hidden sections (sections starting with "_")
            if section_name.startswith("_"):
                # Process fields but don't display the section
                self._process_hidden_section(section_name, section_inputs)
                continue

            # Create section (pass self as parent to avoid widget hierarchy issues)
            section_widget, section_height = self._create_section(
                section_name, section_inputs, self
            )

            # Add to target layout
            target_layout.addWidget(section_widget)
            current_row += section_height + 1

        # After all sections are created, connect class definition and transition widgets
        self._connect_class_definition_and_transitions()

        # After all sections are created, connect dynamic_scenario_checkbox widgets
        self._connect_dynamic_scenario_checkboxes()

        return current_row

    def _connect_class_definition_and_transitions(self):
        """Connect ClassDefinitionTableWidget with TransitionTableWidget"""
        # Check if both widgets exist
        if 'entries' in self.field_widgets and 'transitions' in self.field_widgets:
            class_def_widget = self.field_widgets['entries']
            transition_widget = self.field_widgets['transitions']

            # Check if they are the correct widget types
            from ..widgets.class_definition_table import ClassDefinitionTableWidget
            from ..widgets.transition_table import TransitionTableWidget

            if isinstance(class_def_widget, ClassDefinitionTableWidget) and isinstance(transition_widget, TransitionTableWidget):
                # Function to update reclass keys in transition widget
                def update_transition_keys():
                    entries = class_def_widget.get_value()
                    # Pass entries directly to transition widget
                    # It will extract reclassKeys and regenerate the table
                    transition_widget.set_reclass_keys_from_entries(entries)

                # Connect value changed signal
                class_def_widget.value_changed.connect(update_transition_keys)

                # Initial update
                update_transition_keys()

    def _connect_dynamic_scenario_checkboxes(self):
        """Connect DynamicScenarioCheckbox widgets to their dependent fields.

        This is called after all sections are created to ensure all dependent widgets exist.
        Connects base_directory and rates_file fields to update scenarios dynamically.
        """
        # Find all dynamic_scenario_checkbox widgets
        for param_name, config in self.field_configs.items():
            if config.entry_type != "dynamic_scenario_checkbox":
                continue

            scenario_widget = self.field_widgets.get(param_name)

            if not scenario_widget:
                continue

            # Connect base_directory_field
            base_directory_field = getattr(config, 'base_directory_field', None)
            if base_directory_field:
                base_dir_widget = self.field_widgets.get(base_directory_field)
                if base_dir_widget and hasattr(scenario_widget, 'update_base_directory'):
                    if hasattr(base_dir_widget, 'value_changed'):
                        base_dir_widget.value_changed.connect(
                            lambda w=scenario_widget, b=base_dir_widget: w.update_base_directory(b.get_value() if hasattr(b, 'get_value') else "")
                        )
                    # Initialize with current value
                    if hasattr(base_dir_widget, 'get_value'):
                        initial_base_dir = base_dir_widget.get_value()
                        if initial_base_dir:
                            scenario_widget.update_base_directory(initial_base_dir)

            # Connect rates_file_field
            rates_file_field = getattr(config, 'rates_file_field', None)
            if rates_file_field:
                rates_file_widget = self.field_widgets.get(rates_file_field)
                if rates_file_widget and hasattr(scenario_widget, 'update_rates_file'):
                    if hasattr(rates_file_widget, 'value_changed'):
                        rates_file_widget.value_changed.connect(
                            lambda w=scenario_widget, rf=rates_file_widget: w.update_rates_file(rf.get_value() if hasattr(rf, 'get_value') else "")
                        )
                    # Initialize with current value
                    if hasattr(rates_file_widget, 'get_value'):
                        initial_rates_file = rates_file_widget.get_value()
                        if initial_rates_file:
                            scenario_widget.update_rates_file(initial_rates_file)

    def _process_hidden_section(self, section_name: str, section_inputs: List[Dict]):
        """Process hidden section fields without creating visible widgets"""
        for input_dict in section_inputs:
            for param_name, param_config in input_dict.items():
                # Create field configuration
                config = FieldConfig(
                    label_text=param_config.get("label_text", param_name),
                    entry_type=param_config.get("entry_type", "text entry"),
                    required=param_config.get("required", False),
                    default_value=param_config.get("default_value", ""),
                    dropdown_options=param_config.get("dropdown_options"),
                    extension=param_config.get("extension"),
                    value_type=param_config.get("value_type", str),
                    num_element_list=param_config.get("num_element_list"),
                    labels_list=param_config.get("labels_list"),
                    description=param_config.get("description"),
                    show_sheet_selector=param_config.get("show_sheet_selector", True),
                    show_file_browser=param_config.get("show_file_browser", True),
                    file_extension=param_config.get("file_extension"),
                    subfolder=param_config.get("subfolder"),
                    allow_multiple=param_config.get("allow_multiple", False),
                    parent_folder_field=param_config.get("parent_folder_field"),
                    pattern=param_config.get("pattern"),
                    display_column=param_config.get("display_column"),
                    value_column=param_config.get("value_column"),
                    sheet_name=param_config.get("sheet_name"),
                    excel_file_field=param_config.get("excel_file_field"),
                    strip_extension=param_config.get("strip_extension", True),
                    parent_folder_fallback=param_config.get("parent_folder_fallback"),
                    subfolder_fallback=param_config.get("subfolder_fallback"),
                    structure_name=param_config.get("structure_name"),
                    base_folder_name=param_config.get("base_folder_name"),
                    metadata_target_fields=param_config.get("metadata_target_fields"),
                    ui_only=param_config.get("ui_only", False),
                    auto_select_field=param_config.get("auto_select_field"),
                    auto_select_pattern_map=param_config.get("auto_select_pattern_map"),
                    read_only=param_config.get("read_only", False),
                    # DynamicScenarioCheckbox fields
                    rates_file_field=param_config.get("rates_file_field"),
                    base_directory_field=param_config.get("base_directory_field"),
                    # GroupedCheckbox fields
                    structure=param_config.get("structure")
                )

                # Store configuration
                self.field_configs[param_name] = config

                # Create a hidden widget using the HiddenWidget class defined above
                try:
                    hidden_widget = HiddenWidget(default_value=config.default_value)
                    hidden_widget.setVisible(False)

                    # Store widget reference
                    self.field_widgets[param_name] = hidden_widget

                except Exception as e:
                    logger.error(f"Failed to create hidden widget for {param_name}: {e}")

    def _create_section(self, section_name: str, section_inputs: List[Dict], parent_widget):
        """Create a collapsible section with form fields"""
        # Create collapsible group box
        group_box = CollapsibleGroupBox(section_name.upper(), parent_widget)
        
        # Set initial expanded state
        section_key = section_name.upper()
        is_expanded = self.section_defaults.get(section_key, True)
        group_box.setChecked(is_expanded)
        
        # Create content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(5, 5, 5, 5)
        content_layout.setSpacing(8)
        
        for input_dict in section_inputs:
            for param_name, param_config in input_dict.items():
                # Create field configuration
                config = FieldConfig(
                    label_text=param_config.get("label_text", param_name),
                    entry_type=param_config.get("entry_type", "text entry"),
                    required=param_config.get("required", False),
                    default_value=param_config.get("default_value", ""),
                    dropdown_options=param_config.get("dropdown_options"),
                    extension=param_config.get("extension"),
                    value_type=param_config.get("value_type", str),
                    num_element_list=param_config.get("num_element_list"),
                    labels_list=param_config.get("labels_list"),
                    description=param_config.get("description"),
                    show_sheet_selector=param_config.get("show_sheet_selector", True),
                    show_file_browser=param_config.get("show_file_browser", True),
                    file_extension=param_config.get("file_extension"),
                    subfolder=param_config.get("subfolder"),
                    allow_multiple=param_config.get("allow_multiple", False),
                    parent_folder_field=param_config.get("parent_folder_field"),
                    pattern=param_config.get("pattern"),
                    display_column=param_config.get("display_column"),
                    value_column=param_config.get("value_column"),
                    sheet_name=param_config.get("sheet_name"),
                    excel_file_field=param_config.get("excel_file_field"),
                    strip_extension=param_config.get("strip_extension", True),
                    parent_folder_fallback=param_config.get("parent_folder_fallback"),
                    subfolder_fallback=param_config.get("subfolder_fallback"),
                    structure_name=param_config.get("structure_name"),
                    base_folder_name=param_config.get("base_folder_name"),
                    metadata_target_fields=param_config.get("metadata_target_fields"),
                    ui_only=param_config.get("ui_only", False),
                    auto_select_field=param_config.get("auto_select_field"),
                    auto_select_pattern_map=param_config.get("auto_select_pattern_map"),
                    read_only=param_config.get("read_only", False),
                    # DynamicScenarioCheckbox fields
                    rates_file_field=param_config.get("rates_file_field"),
                    base_directory_field=param_config.get("base_directory_field"),
                    # GroupedCheckbox fields
                    structure=param_config.get("structure")
                )

                # Store configuration
                self.field_configs[param_name] = config

                # Create field container
                field_container = QWidget()
                field_layout = QVBoxLayout(field_container)
                field_layout.setContentsMargins(0, 0, 0, 0)
                field_layout.setSpacing(3)
                
                # Create label
                label_widget = WidgetFactory.create_label(field_container, config)
                field_layout.addWidget(label_widget)
                
                # Create input widget
                try:
                    input_widget = WidgetFactory.create_widget(field_container, config, 0)
                    field_layout.addWidget(input_widget)
                    
                    # Store widget reference
                    self.field_widgets[param_name] = input_widget
                    
                    # Connect value changes
                    if hasattr(input_widget, 'value_changed'):
                        input_widget.value_changed.connect(self.values_changed)
                    
                    # Set default value
                    if config.default_value and hasattr(input_widget, 'set_value'):
                        input_widget.set_value(config.default_value)
                
                except Exception as e:
                    logger.error(f"Failed to create widget for {param_name}: {e}")
                    error_label = QLabel(f"Error creating widget: {str(e)}")
                    error_label.setStyleSheet("QLabel { color: red; }")
                    field_layout.addWidget(error_label)
                
                # Add field container to main layout
                content_layout.addWidget(field_container)

        # After all widgets are created, connect subfolder_file_dropdown widgets to their parent folder fields
        for param_name, config in self.field_configs.items():
            if config.entry_type == "subfolder_file_dropdown" and config.parent_folder_field:
                dropdown_widget = self.field_widgets.get(param_name)
                parent_widget = self.field_widgets.get(config.parent_folder_field)

                if dropdown_widget and parent_widget and hasattr(dropdown_widget, 'update_parent_folder'):
                    # Connect parent widget value changes to dropdown update
                    if hasattr(parent_widget, 'value_changed'):
                        parent_widget.value_changed.connect(
                            lambda w=dropdown_widget, p=parent_widget: w.update_parent_folder(p.get_value() if hasattr(p, 'get_value') else "")
                        )

                    # Initialize with current parent value
                    if hasattr(parent_widget, 'get_value'):
                        initial_value = parent_widget.get_value()
                        if initial_value:
                            dropdown_widget.update_parent_folder(initial_value)

                # Connect auto_select_field if specified
                if hasattr(config, 'auto_select_field') and config.auto_select_field:
                    auto_select_widget = self.field_widgets.get(config.auto_select_field)

                    if auto_select_widget and hasattr(dropdown_widget, 'update_auto_select_value'):
                        # Connect auto_select widget value changes to dropdown auto-selection
                        if hasattr(auto_select_widget, 'value_changed'):
                            auto_select_widget.value_changed.connect(
                                lambda w=dropdown_widget, a=auto_select_widget: w.update_auto_select_value(a.get_value() if hasattr(a, 'get_value') else "")
                            )

                        # Initialize with current auto_select value
                        if hasattr(auto_select_widget, 'get_value'):
                            initial_auto_value = auto_select_widget.get_value()
                            if initial_auto_value:
                                dropdown_widget.update_auto_select_value(initial_auto_value)

            # Connect excel_column_dropdown widgets to their parent folder and excel file fields
            elif config.entry_type == "excel_column_dropdown" and (config.parent_folder_field or config.excel_file_field):
                dropdown_widget = self.field_widgets.get(param_name)

                # Connect parent folder field
                if config.parent_folder_field:
                    parent_widget = self.field_widgets.get(config.parent_folder_field)
                    if dropdown_widget and parent_widget and hasattr(dropdown_widget, 'update_parent_folder'):
                        if hasattr(parent_widget, 'value_changed'):
                            parent_widget.value_changed.connect(
                                lambda w=dropdown_widget, p=parent_widget: w.update_parent_folder(p.get_value() if hasattr(p, 'get_value') else "")
                            )
                        # Initialize with current value
                        if hasattr(parent_widget, 'get_value'):
                            initial_value = parent_widget.get_value()
                            if initial_value:
                                dropdown_widget.update_parent_folder(initial_value)

                # Connect Excel file field
                if config.excel_file_field:
                    excel_widget = self.field_widgets.get(config.excel_file_field)
                    if dropdown_widget and excel_widget and hasattr(dropdown_widget, 'update_excel_file'):
                        if hasattr(excel_widget, 'value_changed'):
                            excel_widget.value_changed.connect(
                                lambda w=dropdown_widget, e=excel_widget: w.update_excel_file(e.get_value() if hasattr(e, 'get_value') else "")
                            )
                        # Initialize with current value
                        if hasattr(excel_widget, 'get_value'):
                            initial_value = excel_widget.get_value()
                            if initial_value:
                                dropdown_widget.update_excel_file(initial_value)

            # Connect excel_column_selector widgets to their parent folder and excel file fields
            elif config.entry_type == "excel_column_selector" and (config.parent_folder_field or config.excel_file_field):
                selector_widget = self.field_widgets.get(param_name)

                # Connect parent folder field
                if config.parent_folder_field:
                    parent_widget = self.field_widgets.get(config.parent_folder_field)
                    if selector_widget and parent_widget and hasattr(selector_widget, 'update_parent_folder'):
                        if hasattr(parent_widget, 'value_changed'):
                            parent_widget.value_changed.connect(
                                lambda w=selector_widget, p=parent_widget: w.update_parent_folder(p.get_value() if hasattr(p, 'get_value') else "")
                            )
                        # Initialize with current value
                        if hasattr(parent_widget, 'get_value'):
                            initial_value = parent_widget.get_value()
                            if initial_value:
                                selector_widget.update_parent_folder(initial_value)

                # Connect Excel file field
                if config.excel_file_field:
                    excel_widget = self.field_widgets.get(config.excel_file_field)
                    if selector_widget and excel_widget and hasattr(selector_widget, 'update_excel_file'):
                        if hasattr(excel_widget, 'value_changed'):
                            excel_widget.value_changed.connect(
                                lambda w=selector_widget, e=excel_widget: w.update_excel_file(e.get_value() if hasattr(e, 'get_value') else "")
                            )
                        # Initialize with current value
                        if hasattr(excel_widget, 'get_value'):
                            initial_value = excel_widget.get_value()
                            if initial_value:
                                selector_widget.update_excel_file(initial_value)

            # Connect folder_file_checkbox widgets to their parent folder fields
            elif config.entry_type == "folder_file_checkbox" and config.parent_folder_field:
                checkbox_widget = self.field_widgets.get(param_name)
                parent_widget = self.field_widgets.get(config.parent_folder_field)

                if checkbox_widget and parent_widget and hasattr(checkbox_widget, 'update_parent_folder'):
                    if hasattr(parent_widget, 'value_changed'):
                        parent_widget.value_changed.connect(
                            lambda w=checkbox_widget, p=parent_widget: w.update_parent_folder(p.get_value() if hasattr(p, 'get_value') else "")
                        )
                    # Initialize with current value
                    if hasattr(parent_widget, 'get_value'):
                        initial_value = parent_widget.get_value()
                        if initial_value:
                            checkbox_widget.update_parent_folder(initial_value)

                # Connect fallback parent folder field if specified
                parent_folder_fallback = getattr(config, 'parent_folder_fallback', None)
                if parent_folder_fallback and hasattr(checkbox_widget, 'update_fallback_parent_folder'):
                    fallback_widget = self.field_widgets.get(parent_folder_fallback)
                    if fallback_widget:
                        if hasattr(fallback_widget, 'value_changed'):
                            fallback_widget.value_changed.connect(
                                lambda w=checkbox_widget, p=fallback_widget: w.update_fallback_parent_folder(p.get_value() if hasattr(p, 'get_value') else "")
                            )
                        # Initialize with current fallback value
                        if hasattr(fallback_widget, 'get_value'):
                            fallback_initial_value = fallback_widget.get_value()
                            if fallback_initial_value:
                                checkbox_widget.update_fallback_parent_folder(fallback_initial_value)

            # Connect folder_structure_generator widgets to their parent folder fields
            elif config.entry_type == "folder_structure_generator" and config.parent_folder_field:
                generator_widget = self.field_widgets.get(param_name)
                parent_widget = self.field_widgets.get(config.parent_folder_field)

                if generator_widget and parent_widget and hasattr(generator_widget, 'update_parent_folder'):
                    if hasattr(parent_widget, 'value_changed'):
                        parent_widget.value_changed.connect(
                            lambda w=generator_widget, p=parent_widget: w.update_parent_folder(p.get_value() if hasattr(p, 'get_value') else "")
                        )
                    # Initialize with current value
                    if hasattr(parent_widget, 'get_value'):
                        initial_value = parent_widget.get_value()
                        if initial_value:
                            generator_widget.update_parent_folder(initial_value)

            # Connect model_folder_selector widgets to their parent folder fields and metadata target fields
            elif config.entry_type == "model_folder_selector" and config.parent_folder_field:
                selector_widget = self.field_widgets.get(param_name)
                parent_widget = self.field_widgets.get(config.parent_folder_field)

                # Connect to parent folder
                if selector_widget and parent_widget and hasattr(selector_widget, 'update_parent_folder'):
                    if hasattr(parent_widget, 'value_changed'):
                        parent_widget.value_changed.connect(
                            lambda w=selector_widget, p=parent_widget: w.update_parent_folder(p.get_value() if hasattr(p, 'get_value') else "")
                        )
                    # Initialize with current value
                    if hasattr(parent_widget, 'get_value'):
                        initial_value = parent_widget.get_value()
                        if initial_value:
                            selector_widget.update_parent_folder(initial_value)

                # Connect metadata to target fields
                if config.metadata_target_fields and hasattr(selector_widget, 'metadata_changed'):
                    def update_target_fields(metadata, targets=config.metadata_target_fields):
                        # Update project_name field
                        if 'project_name' in targets:
                            target_field = targets['project_name']
                            target_widget = self.field_widgets.get(target_field)
                            if target_widget and hasattr(target_widget, 'set_value'):
                                project_name = metadata.get('project_name', '')
                                target_widget.set_value(project_name)

                        # Update version field
                        if 'version' in targets:
                            target_field = targets['version']
                            target_widget = self.field_widgets.get(target_field)
                            if target_widget and hasattr(target_widget, 'set_value'):
                                version = metadata.get('version', '')
                                target_widget.set_value(version)

                        # Update use_standardized_rasters field
                        if 'use_standardized_rasters' in targets:
                            target_field = targets['use_standardized_rasters']
                            target_widget = self.field_widgets.get(target_field)
                            if target_widget and hasattr(target_widget, 'set_value'):
                                use_std = metadata.get('use_standardized_rasters', False)
                                target_widget.set_value("1" if use_std else "0")

                        # Update period_to_model dropdown options and selection
                        if 'period_options' in targets:
                            target_field = targets['period_options']
                            target_widget = self.field_widgets.get(target_field)
                            if target_widget and hasattr(target_widget, 'set_options'):  # It's a dropdown wrapper
                                period_options = metadata.get('period_options', [])
                                if period_options:
                                    # Block signals to avoid triggering value_changed during update
                                    target_widget.blockSignals(True)
                                    # Clear and repopulate dropdown
                                    target_widget.set_options(period_options)
                                    # Set first option as selected
                                    if hasattr(target_widget, 'set_value') and len(period_options) > 0:
                                        target_widget.set_value(period_options[0])
                                    target_widget.blockSignals(False)
                                    # Manually emit value_changed signal to update dependent fields
                                    if hasattr(target_widget, 'value_changed'):
                                        target_widget.value_changed.emit()

                    selector_widget.metadata_changed.connect(update_target_fields)

            # Note: dynamic_scenario_checkbox connections are done after all sections are created
            # in _connect_dynamic_scenario_checkboxes() to ensure all dependent widgets exist

        # Set content widget
        group_box.setContentWidget(content_widget)
        
        # Count the number of fields for height calculation
        field_count = sum(len(input_dict) for input_dict in section_inputs)
        
        return group_box, field_count
    
    def get_all_values(self):
        """Get all current field values, excluding ui_only fields (for passing to functions)"""
        values = {}
        for param_name, widget in self.field_widgets.items():
            # Skip ui_only fields (e.g., folder_structure_generator, model_folder_selector)
            config = self.field_configs.get(param_name)
            if config and config.ui_only:
                continue

            try:
                if hasattr(widget, 'get_value'):
                    values[param_name] = widget.get_value()
                else:
                    values[param_name] = ""
            except Exception as e:
                logger.warning(f"Failed to get value for {param_name}: {e}")
                values[param_name] = ""

        return values

    def get_all_values_for_config(self):
        """Get ALL field values including ui_only fields (for saving/loading configurations)"""
        values = {}
        for param_name, widget in self.field_widgets.items():
            try:
                if hasattr(widget, 'get_value'):
                    values[param_name] = widget.get_value()
                else:
                    values[param_name] = ""
            except Exception as e:
                logger.warning(f"Failed to get value for {param_name}: {e}")
                values[param_name] = ""

        return values
    
    def set_values(self, values: Dict[str, str]):
        """Set field values from dictionary in dependency order"""
        # Classify fields by dependency level
        independent_fields = []
        dependent_fields_by_level = {}  # level -> [field_names]

        def get_dependency_level(param_name, visited=None):
            """Recursively calculate dependency level (0 = independent)"""
            if visited is None:
                visited = set()

            if param_name in visited:
                return 0  # Circular dependency, treat as independent

            if param_name not in self.field_configs:
                return 0  # Unknown field, treat as independent

            config = self.field_configs[param_name]

            # Check for dependencies
            dependencies = []
            if config.parent_folder_field:
                dependencies.append(config.parent_folder_field)
            if config.excel_file_field:
                dependencies.append(config.excel_file_field)

            if not dependencies and config.entry_type not in ['excel_column_dropdown', 'subfolder_file_dropdown',
                                                               'folder_file_checkbox', 'excel_column_selector',
                                                               'model_folder_selector', 'dynamic_scenario_checkbox']:
                return 0  # No dependencies

            # Calculate max dependency level + 1
            visited.add(param_name)
            max_dep_level = 0
            for dep_field in dependencies:
                dep_level = get_dependency_level(dep_field, visited.copy())
                max_dep_level = max(max_dep_level, dep_level)

            return max_dep_level + 1

        # Classify all fields
        for param_name in values.keys():
            level = get_dependency_level(param_name)
            if level == 0:
                independent_fields.append(param_name)
            else:
                if level not in dependent_fields_by_level:
                    dependent_fields_by_level[level] = []
                dependent_fields_by_level[level].append(param_name)

        # Set independent fields first
        for param_name in independent_fields:
            if param_name in self.field_widgets:
                widget = self.field_widgets[param_name]
                try:
                    if hasattr(widget, 'set_value'):
                        widget.set_value(values[param_name])
                except Exception as e:
                    logger.warning(f"Failed to set value for {param_name}: {e}")

        # Process dependent fields level by level (ensures dependencies are set before dependents)
        for level in sorted(dependent_fields_by_level.keys()):
            dependent_fields_at_level = dependent_fields_by_level[level]

            # First, trigger updates for all fields at this level
            for param_name in dependent_fields_at_level:
                if param_name in self.field_widgets:
                    widget = self.field_widgets[param_name]
                    config = self.field_configs.get(param_name)

                    if config:
                        # For widgets that depend on both parent_folder and excel_file,
                        # we need to set both before triggering _load_data()
                        needs_parent_folder = config.parent_folder_field and hasattr(widget, 'update_parent_folder')
                        needs_excel_file = config.excel_file_field and hasattr(widget, 'update_excel_file')

                        if needs_parent_folder and needs_excel_file:
                            # Set both parent folder and excel file, then force reload
                            parent_widget = self.field_widgets.get(config.parent_folder_field)
                            excel_widget = self.field_widgets.get(config.excel_file_field)

                            if parent_widget and excel_widget:
                                parent_folder = parent_widget.get_value() if hasattr(parent_widget, 'get_value') else ""
                                excel_file = excel_widget.get_value() if hasattr(excel_widget, 'get_value') else ""

                                if parent_folder and excel_file:
                                    try:
                                        # Set parent folder and excel filename directly
                                        widget.parent_folder = parent_folder
                                        widget.excel_filename = excel_file
                                        # Force data load
                                        if hasattr(widget, '_load_data'):
                                            widget._load_data()
                                    except Exception as e:
                                        logger.warning(f"Failed to trigger data load for {param_name}: {e}")
                        else:
                            # Only one dependency - use normal update methods
                            if needs_excel_file:
                                excel_widget = self.field_widgets.get(config.excel_file_field)
                                if excel_widget:
                                    excel_file = excel_widget.get_value() if hasattr(excel_widget, 'get_value') else ""
                                    if excel_file:
                                        try:
                                            widget.update_excel_file(excel_file)
                                        except Exception as e:
                                            logger.warning(f"Failed to trigger excel update for {param_name}: {e}")

                            if needs_parent_folder:
                                parent_widget = self.field_widgets.get(config.parent_folder_field)
                                if parent_widget:
                                    parent_folder = parent_widget.get_value() if hasattr(parent_widget, 'get_value') else ""
                                    if parent_folder:
                                        try:
                                            widget.update_parent_folder(parent_folder)
                                        except Exception as e:
                                            logger.warning(f"Failed to trigger parent folder update for {param_name}: {e}")

            # Then set values for all fields at this level
            for param_name in dependent_fields_at_level:
                if param_name in self.field_widgets:
                    widget = self.field_widgets[param_name]
                    try:
                        if hasattr(widget, 'set_value'):
                            widget.set_value(values[param_name])
                    except Exception as e:
                        logger.warning(f"Failed to set value for {param_name}: {e}")
    
    def reset_to_defaults(self):
        """Reset all fields to their default values"""
        for param_name, config in self.field_configs.items():
            if param_name in self.field_widgets:
                widget = self.field_widgets[param_name]
                # Use config.default_value directly, only fallback to "" if it's None
                default_val = config.default_value if config.default_value is not None else ""
                try:
                    if hasattr(widget, 'set_value'):
                        widget.set_value(default_val)
                except Exception as e:
                    logger.warning(f"Failed to reset {param_name} to default: {e}")
    
    def validate_required_fields(self):
        """Validate that all required fields have values"""
        errors = []
        
        for param_name, config in self.field_configs.items():
            if config.required:
                widget = self.field_widgets.get(param_name)
                if widget and hasattr(widget, 'get_value'):
                    value = widget.get_value()
                    if not value or str(value).strip() == "":
                        errors.append(f"{config.label_text} is required")
        
        return errors
    
    def save_configuration(self, file_path: str, comments: str = ""):
        """Save current configuration to file with test_module.txt formatting"""
        try:
            # Use get_all_values_for_config to include ui_only fields (like model_folder)
            values = self.get_all_values_for_config()

            # Use enhanced formatter if available
            if ConfigJsonFormatter:
                from ..utils.json_formatter import create_formatted_json
                formatted_json = create_formatted_json(
                    self.module_title, values, self.field_configs, self.sections, comments=comments
                )

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(formatted_json)
            else:
                # Fallback to simple format
                config_data = {
                    "module": self.module_title,
                    "saved_on": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "comments": comments,
                    "arguments": values
                }

                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, indent=2, ensure_ascii=False)

            return True
        except Exception:
            return False

    def load_configuration(self, file_path: str):
        """Load configuration from file (supports all formats)"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Check if it's the new format with metadata
            if isinstance(data, dict) and "arguments" in data:
                arguments = data["arguments"]
                config_module = data.get('module', 'Unknown Module')

                # Validate module compatibility
                if config_module != self.module_title:
                    # Show warning dialog to user
                    reply = show_question_dialog(
                        self,
                        "Module Mismatch Warning",
                        f"This configuration file is for '{config_module}' module,\n"
                        f"but you're currently using '{self.module_title}' module.\n\n"
                        f"Some fields may not match or work correctly.\n\n"
                        f"Do you want to continue loading anyway?"
                    )

                    if not reply:
                        return None

                # Restore filenames for 'dynamic rows with file' fields
                formatter = ConfigJsonFormatter(self.field_configs, self.sections)
                restored_arguments = formatter.restore_filenames_from_json(arguments)

                # Check if arguments are in the new structured format (with sections)
                values = self._extract_values_from_structured_format(restored_arguments)
            else:
                # Old format - direct values
                # Also restore filenames for legacy format if needed
                formatter = ConfigJsonFormatter(self.field_configs, self.sections)
                restored_data = formatter.restore_filenames_from_json(data)
                values = restored_data

            self.set_values(values)
            return True
        except Exception:
            return False

    def _extract_values_from_structured_format(self, arguments: dict) -> dict:
        """
        Extract simple key-value pairs from the structured format.
        Handles both old simple format and new structured format.
        Converts complex widget values to expected string formats.
        """
        values = {}
        
        # Check if this looks like structured format (sections with field objects)
        is_structured = False
        for key, value in arguments.items():
            if isinstance(value, dict) and any(field_key in value for field_key in ["value", "type", "label"]):
                # This looks like structured format
                is_structured = True
                break
            elif isinstance(value, dict):
                # Check if it's a section containing structured fields
                for field_name, field_data in value.items():
                    if isinstance(field_data, dict) and "value" in field_data:
                        is_structured = True
                        break
                if is_structured:
                    break
        
        if is_structured:
            # New structured format - extract values and convert complex widget formats
            for section_or_field, data in arguments.items():
                if isinstance(data, dict):
                    if "value" in data:
                        # Direct field - convert value to widget-expected format
                        widget_type = data.get("type", "text entry")
                        raw_value = data["value"]
                        values[section_or_field] = self._convert_value_for_widget(raw_value, widget_type, section_or_field)
                    else:
                        # Section containing fields
                        for field_name, field_data in data.items():
                            if isinstance(field_data, dict) and "value" in field_data:
                                widget_type = field_data.get("type", "text entry")
                                raw_value = field_data["value"]
                                values[field_name] = self._convert_value_for_widget(raw_value, widget_type, field_name)
        else:
            # Simple format - convert values if they are complex types
            for key, value in arguments.items():
                # Try to determine widget type from field configs
                field_config = self.field_configs.get(key)
                if field_config:
                    widget_type = field_config.entry_type
                    values[key] = self._convert_value_for_widget(value, widget_type, key)
                else:
                    values[key] = value
        
        return values
    
    def _convert_value_for_widget(self, value, widget_type: str, field_name: str = None):
        """
        Convert a value from JSON format to the format expected by the widget.
        
        Args:
            value: The value from JSON (could be list, dict, string, etc.)
            widget_type: The type of widget that will receive this value
            field_name: The field name to look up specific config
            
        Returns:
            Value in the format expected by the widget's set_value method
        """
        import json
        
        if widget_type == "browse multiple":
            # Multiple file browser expects JSON string of list
            if isinstance(value, list):
                return json.dumps(value)
            elif isinstance(value, str):
                return value  # Already in string format
            else:
                return "[]"
        
        elif widget_type == "dynamic rows":
            # Dynamic rows expect JSON string of list of lists
            if isinstance(value, list):
                return json.dumps(value)
            elif isinstance(value, str):
                return value  # Already in string format
            else:
                return "[]"
        
        elif widget_type == "dynamic rows with file":
            # Dynamic rows with file expect JSON string of dict
            if isinstance(value, list):
                # Convert list format back to dict format expected by widget
                result = {}
                for i, row in enumerate(value):
                    if isinstance(row, list) and len(row) >= 1:
                        # Extract file path from last element, values from rest
                        file_path = row[-1] if len(row) > 1 else ""
                        values = row[:-1] if len(row) > 1 else row
                        result[f"row_{i}"] = {
                            "values": values,
                            "file_path": file_path
                        }
                return json.dumps(result)
            elif isinstance(value, dict):
                return json.dumps(value)
            elif isinstance(value, str):
                return value  # Already in string format
            else:
                return "{}"
        
        elif widget_type == "list entry":
            # List entry expects comma-separated string
            if isinstance(value, dict):
                # Convert dict back to comma-separated values
                # Use the specific field name to get the correct config
                labels_list = None
                if field_name and field_name in self.field_configs:
                    field_config = self.field_configs[field_name]
                    if hasattr(field_config, 'labels_list') and field_config.labels_list:
                        labels_list = field_config.labels_list
                
                if labels_list:
                    values_list = []
                    for label in labels_list:
                        values_list.append(value.get(label, ""))
                    return ", ".join(values_list)
                else:
                    # Fallback: just join the values in order
                    return ", ".join(str(v) for v in value.values())
            elif isinstance(value, str):
                return value  # Already in string format
            else:
                return ""
        
        elif widget_type in ["multiple checkbox", "grouped_checkbox"]:
            # Multiple checkbox / Grouped checkbox expects JSON string of list
            if isinstance(value, list):
                return json.dumps(value)
            elif isinstance(value, str):
                return value  # Already in string format
            else:
                return "[]"

        elif widget_type == "class_definition_table":
            # Class definition table expects list of dicts directly
            if isinstance(value, list):
                return value  # Return list directly
            elif isinstance(value, str):
                # Parse string to list - try JSON first, then ast.literal_eval for Python syntax
                try:
                    return json.loads(value)
                except:
                    # Try using ast.literal_eval for Python syntax (single quotes)
                    try:
                        import ast
                        return ast.literal_eval(value)
                    except:
                        return []
            else:
                return []

        elif widget_type == "transition_table":
            # Transition table expects list of dicts directly
            if isinstance(value, list):
                return value  # Return list directly
            elif isinstance(value, str):
                # Parse string to list - try JSON first, then ast.literal_eval for Python syntax
                try:
                    return json.loads(value)
                except:
                    # Try using ast.literal_eval for Python syntax (single quotes)
                    try:
                        import ast
                        return ast.literal_eval(value)
                    except:
                        return []
            else:
                return []

        else:
            # For other widget types, return as-is (mostly strings)
            return value