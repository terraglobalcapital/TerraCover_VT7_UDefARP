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
#   Simplified widget factory with only required widgets
#
#   This code is proprietary and confidential.
#   Unauthorized copying or distribution is prohibited.
#
# ------------------------------------------------------------------------


"""
Widget factory for creating different types of form widgets in PyQt6
Simplified version for VT7 UDef-ARP Standalone
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QComboBox, QCheckBox,
                             QFileDialog, QFrame, QSpinBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent
import os


class AutoCompleteLineEdit(QLineEdit):
    """QLineEdit with auto-completion for paired characters like quotes, parentheses, and brackets"""

    # Map of opening characters to their closing counterparts
    PAIR_MAP = {
        '(': ')',
        '[': ']',
        '{': '}',
        '"': '"',
        "'": "'",
    }

    def __init__(self, parent=None):
        super().__init__(parent)

    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press events for auto-completion"""
        key_text = event.text()

        # Check if the key is an opening character
        if key_text in self.PAIR_MAP:
            closing_char = self.PAIR_MAP[key_text]
            cursor_pos = self.cursorPosition()
            current_text = self.text()
            selected_text = self.selectedText()

            if selected_text:
                # Wrap selected text with the pair
                selection_start = self.selectionStart()
                new_text = (current_text[:selection_start] +
                           key_text + selected_text + closing_char +
                           current_text[selection_start + len(selected_text):])
                self.setText(new_text)
                # Position cursor after the closing character
                self.setCursorPosition(selection_start + len(selected_text) + 2)
            else:
                # Insert both opening and closing characters
                new_text = current_text[:cursor_pos] + key_text + closing_char + current_text[cursor_pos:]
                self.setText(new_text)
                # Position cursor between the pair
                self.setCursorPosition(cursor_pos + 1)
            return

        # Check if typing a closing character that's already there (skip over it)
        if key_text in self.PAIR_MAP.values():
            cursor_pos = self.cursorPosition()
            current_text = self.text()

            # Check if the next character is the same closing character
            if cursor_pos < len(current_text) and current_text[cursor_pos] == key_text:
                # Skip over the existing closing character
                self.setCursorPosition(cursor_pos + 1)
                return

        # Handle backspace - delete pair if cursor is between them
        if event.key() == Qt.Key.Key_Backspace:
            cursor_pos = self.cursorPosition()
            current_text = self.text()

            if cursor_pos > 0 and cursor_pos < len(current_text):
                prev_char = current_text[cursor_pos - 1]
                next_char = current_text[cursor_pos]

                # Check if we're between a pair
                if prev_char in self.PAIR_MAP and self.PAIR_MAP[prev_char] == next_char:
                    # Delete both characters
                    new_text = current_text[:cursor_pos - 1] + current_text[cursor_pos + 1:]
                    self.setText(new_text)
                    self.setCursorPosition(cursor_pos - 1)
                    return

        # Default behavior for all other keys
        super().keyPressEvent(event)


class NoScrollComboBox(QComboBox):
    """QComboBox that ignores wheel scroll events to prevent accidental changes."""

    def wheelEvent(self, event):
        """Ignore wheel events to prevent accidental value changes when scrolling."""
        event.ignore()


from ..core.field_config import FieldConfig
from ..frame.tool_tip import ToolTipManager
from .multiple_checkbox import MultipleCheckboxWidget
from .grouped_checkbox import GroupedCheckboxWidget


class FieldWidget(QWidget):
    """Base widget for form fields with value tracking"""

    value_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = ""

    def get_value(self):
        return self._value

    def set_value(self, value):
        self._value = str(value)

    def emit_change(self):
        self.value_changed.emit()


class FileWidget(FieldWidget):
    """Widget for file/folder browsing"""

    def __init__(self, parent, config: FieldConfig, browse_type: str):
        super().__init__(parent)
        self.config = config
        self.browse_type = browse_type

        # Set up layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create line edit
        self.line_edit = QLineEdit()
        self.line_edit.setStyleSheet("""
            QLineEdit {
                background-color: #404040;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px 8px;
                color: #ffffff;
            }
            QLineEdit:focus {
                border-color: #4a90e2;
                background-color: #454545;
            }
        """)
        self.line_edit.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.line_edit)

        # Create browse button(s)
        if browse_type in ["browse file", "save file"]:
            self._create_file_button(layout, "Browse File" if "browse" in browse_type else "Save File")
        elif browse_type in ["browse folder", "save folder"]:
            self._create_folder_button(layout, "Browse Folder" if "browse" in browse_type else "Save Folder")
        elif browse_type in ["browse file/folder", "save file/folder"]:
            self._create_file_button(layout, "Browse File" if "browse" in browse_type else "Save File")
            self._create_folder_button(layout, "Browse Folder" if "browse" in browse_type else "Save Folder")

    def _create_file_button(self, layout, text):
        """Create file browse/save button"""
        button = QPushButton(text)
        button.setStyleSheet("""
            QPushButton {
                background-color: #4a90e2;
                border: 1px solid #6ba3e6;
                color: white;
                font-weight: bold;
                padding: 4px 8px;
                border-radius: 4px;
                min-width: 60px;
                max-height: 30px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #6ba3e6;
            }
        """)

        if "save" in text.lower():
            button.clicked.connect(self._save_file)
        else:
            button.clicked.connect(self._browse_file)

        layout.addWidget(button)

    def _create_folder_button(self, layout, text):
        """Create folder browse/save button"""
        button = QPushButton(text)
        button.setStyleSheet("""
            QPushButton {
                background-color: #4a90e2;
                border: 1px solid #6ba3e6;
                color: white;
                font-weight: bold;
                padding: 4px 8px;
                border-radius: 4px;
                min-width: 60px;
                max-height: 30px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #6ba3e6;
            }
        """)

        if "save" in text.lower():
            button.clicked.connect(self._save_folder)
        else:
            button.clicked.connect(self._browse_folder)

        layout.addWidget(button)

    def _get_file_filter(self):
        """Get file filter based on extension"""
        if not self.config.extension or self.config.extension == ".all":
            return "All Files (*.*)"
        elif self.config.extension == ".vector":
            return "Vector Files (*.shp *.gpkg *.geojson *.kml *.gdb)"
        elif self.config.extension == ".raster":
            return "Raster Files (*.tif *.tiff *.img *.hdf *.nc)"
        elif self.config.extension == ".gis":
            return "GIS Files (*.shp *.gpkg *.tif *.tiff *.geojson)"
        elif self.config.extension == ".excel":
            return "Excel/CSV Files (*.xlsx *.xls *.csv)"
        else:
            ext = self.config.extension.replace('.', '')
            return f"{ext.upper()} Files (*{self.config.extension})"

    def _browse_file(self):
        """Browse for file"""
        file_filter = self._get_file_filter()
        from ..core.dialog_theming import get_open_filename
        file_path, _ = get_open_filename(self, "Select File", "", file_filter)
        if file_path:
            self.line_edit.setText(file_path)

    def _save_file(self):
        """Save file dialog"""
        file_filter = self._get_file_filter()
        from ..core.dialog_theming import get_save_filename
        file_path, _ = get_save_filename(self, "Save File", "", file_filter)
        if file_path:
            self.line_edit.setText(file_path)

    def _browse_folder(self):
        """Browse for folder"""
        from ..core.dialog_theming import get_existing_directory
        folder_path = get_existing_directory(self, "Select Folder")
        if folder_path:
            self.line_edit.setText(folder_path)

    def _save_folder(self):
        """Save folder dialog"""
        from ..core.dialog_theming import get_existing_directory
        folder_path = get_existing_directory(self, "Select Output Folder")
        if folder_path:
            self.line_edit.setText(folder_path)

    def _on_text_changed(self):
        """Handle text change"""
        self._value = self.line_edit.text()
        self.emit_change()

    def get_value(self):
        return self.line_edit.text()

    def set_value(self, value):
        self._value = str(value)
        self.line_edit.setText(self._value)


class WidgetFactory:
    """Factory for creating different types of form widgets - Simplified for standalone"""

    @staticmethod
    def create_widget(parent, config: FieldConfig, row: int):
        """Create appropriate widget based on configuration"""
        widget_map = {
            "browse file": lambda: WidgetFactory._create_file_browser(parent, config, "browse file"),
            "browse folder": lambda: WidgetFactory._create_file_browser(parent, config, "browse folder"),
            "browse file/folder": lambda: WidgetFactory._create_file_browser(parent, config, "browse file/folder"),
            "save file": lambda: WidgetFactory._create_file_browser(parent, config, "save file"),
            "save folder": lambda: WidgetFactory._create_file_browser(parent, config, "save folder"),
            "save file/folder": lambda: WidgetFactory._create_file_browser(parent, config, "save file/folder"),
            "dropdown": lambda: WidgetFactory._create_dropdown(parent, config),
            "checkbox": lambda: WidgetFactory._create_checkbox(parent, config),
            "text entry": lambda: WidgetFactory._create_text_entry(parent, config),
            "list entry": lambda: WidgetFactory._create_list_entry(parent, config),
            "multiple checkbox": lambda: WidgetFactory._create_multiple_checkbox(parent, config),
            "grouped_checkbox": lambda: WidgetFactory._create_grouped_checkbox(parent, config),
        }

        if config.entry_type not in widget_map:
            raise ValueError(f"Unknown entry_type: {config.entry_type}. Standalone version supports: {list(widget_map.keys())}")

        return widget_map[config.entry_type]()

    @staticmethod
    def create_label(parent, config: FieldConfig):
        """Create label for widget"""
        label_widget = QWidget(parent)
        layout = QHBoxLayout(label_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create question mark icon if description exists
        if config.description:
            help_icon = QLabel("?")
            help_icon.setFixedSize(18, 18)
            help_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            help_icon.setStyleSheet("""
                QLabel {
                    background-color: #4a90e2;
                    color: white;
                    border-radius: 9px;
                    font-weight: bold;
                    font-size: 12px;
                }
            """)
            help_icon.setCursor(Qt.CursorShape.WhatsThisCursor)

            # Add tooltip
            ToolTipManager.add_tooltip(help_icon, config.description)

            layout.addWidget(help_icon)

        # Create main label
        text = config.label_text
        if config.required:
            text += " *"

        label = QLabel(text)
        label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 12px;
                padding: 2px;
            }
        """)
        label.setWordWrap(False)
        layout.addWidget(label)

        return label_widget

    @staticmethod
    def _create_file_browser(parent, config: FieldConfig, browse_type: str):
        """Create file browser widget"""
        return FileWidget(parent, config, browse_type)

    @staticmethod
    def _create_dropdown(parent, config: FieldConfig):
        """Create dropdown widget"""
        if not config.dropdown_options:
            raise ValueError("dropdown_options is required for dropdown entry type")

        dropdown = NoScrollComboBox(parent)
        dropdown.setStyleSheet("""
            QComboBox {
                background-color: #404040;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px 8px;
                color: #ffffff;
                min-width: 100px;
            }
            QComboBox:hover {
                border-color: #4a90e2;
            }
            QComboBox:focus {
                border-color: #4a90e2;
                background-color: #454545;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left: 1px solid #555555;
                background-color: #404040;
                border-radius: 0px 4px 4px 0px;
            }
            QComboBox QAbstractItemView {
                background-color: #353535;
                border: 1px solid #555555;
                border-radius: 4px;
                color: #ffffff;
                selection-background-color: #4a90e2;
                outline: none;
            }
        """)

        # Add options
        string_options = [str(option) for option in config.dropdown_options]
        dropdown.addItems(string_options)

        # Set default value
        if config.default_value and config.default_value in string_options:
            dropdown.setCurrentText(config.default_value)
        elif string_options:
            dropdown.setCurrentIndex(0)

        # Create wrapper widget
        wrapper = FieldWidget(parent)
        wrapper_layout = QHBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.addWidget(dropdown)
        wrapper_layout.addStretch()

        # Connect signals
        dropdown.currentTextChanged.connect(lambda text: setattr(wrapper, '_value', text))
        dropdown.currentTextChanged.connect(wrapper.emit_change)

        # Override methods
        wrapper.get_value = dropdown.currentText
        wrapper.set_value = lambda value: dropdown.setCurrentText(str(value))

        # Add methods to manipulate dropdown options (for dynamic updates)
        wrapper.clear_options = lambda: dropdown.clear()
        wrapper.add_options = lambda options: dropdown.addItems([str(opt) for opt in options])
        wrapper.set_options = lambda options: (dropdown.clear(), dropdown.addItems([str(opt) for opt in options]))
        wrapper.blockSignals = dropdown.blockSignals
        wrapper._dropdown = dropdown  # Store reference to internal dropdown

        return wrapper

    @staticmethod
    def _create_checkbox(parent, config: FieldConfig):
        """Create checkbox widget"""
        checkbox = QCheckBox(parent)
        checkbox.setStyleSheet("""
            QCheckBox {
                color: #ffffff;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #555555;
                border-radius: 3px;
                background-color: #404040;
            }
            QCheckBox::indicator:hover {
                border-color: #4a90e2;
            }
            QCheckBox::indicator:checked {
                background-color: #4a90e2;
                border-color: #4a90e2;
            }
            QCheckBox::indicator:checked:hover {
                background-color: #6ba3e6;
                border-color: #6ba3e6;
            }
        """)

        # Set default state
        default_checked = config.default_value in ["1", "true", "True", "yes", "Yes", "on", "On"]
        checkbox.setChecked(default_checked)

        # Create wrapper widget
        wrapper = FieldWidget(parent)
        wrapper_layout = QHBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.addWidget(checkbox)
        wrapper_layout.addStretch()

        # Connect signals
        checkbox.toggled.connect(lambda checked: setattr(wrapper, '_value', "1" if checked else "0"))
        checkbox.toggled.connect(wrapper.emit_change)

        # Override methods
        wrapper.get_value = lambda: "1" if checkbox.isChecked() else "0"
        wrapper.set_value = lambda value: checkbox.setChecked(str(value) in ["1", "true", "True", "yes", "Yes", "on", "On"])

        return wrapper

    @staticmethod
    def _create_text_entry(parent, config: FieldConfig):
        """Create simple text entry widget with auto-completion for paired characters"""
        entry = AutoCompleteLineEdit(parent)
        entry.setStyleSheet("""
            QLineEdit {
                background-color: #404040;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px 8px;
                color: #ffffff;
            }
            QLineEdit:focus {
                border-color: #4a90e2;
                background-color: #454545;
            }
        """)

        # Set default value
        if config.default_value:
            entry.setText(config.default_value)

        # Create wrapper widget
        wrapper = FieldWidget(parent)
        wrapper_layout = QHBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.addWidget(entry)

        # Connect signals
        entry.textChanged.connect(lambda text: setattr(wrapper, '_value', text))
        entry.textChanged.connect(wrapper.emit_change)

        # Override methods
        wrapper.get_value = entry.text
        wrapper.set_value = entry.setText

        return wrapper

    @staticmethod
    def _create_list_entry(parent, config: FieldConfig):
        """Create list entry widget"""
        # Calculate number of elements
        if config.labels_list:
            num_elements = len(config.labels_list)
            labels_list = config.labels_list
        elif config.num_element_list:
            num_elements = config.num_element_list
            labels_list = [f"Value {i+1}" for i in range(config.num_element_list)]
        else:
            raise ValueError("Either labels_list or num_element_list is required for 'list entry' type")

        # Create container widget
        container = FieldWidget(parent)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        entries = []
        for i in range(num_elements):
            entry = QLineEdit()
            entry.setPlaceholderText(labels_list[i])
            entry.setStyleSheet("""
                QLineEdit {
                    background-color: #404040;
                    border: 1px solid #555555;
                    border-radius: 4px;
                    padding: 6px 8px;
                    color: #ffffff;
                }
                QLineEdit:focus {
                    border-color: #4a90e2;
                    background-color: #454545;
                }
            """)
            entry.textChanged.connect(lambda: container.emit_change())
            entries.append(entry)
            layout.addWidget(entry)

        # Override methods
        def get_list_value():
            values = []
            for entry in entries:
                value = entry.text().strip()
                values.append(value)
            return ', '.join(values) if any(values) else ""

        def set_list_value(value):
            if not value or value.strip() == "":
                for entry in entries:
                    entry.clear()
                return

            try:
                if value.startswith('[') and value.endswith(']'):
                    import ast
                    values = ast.literal_eval(value)
                else:
                    values = [v.strip().strip("'\"") for v in value.split(',')]

                for i, entry in enumerate(entries):
                    entry.clear()
                    if i < len(values) and values[i]:
                        entry.setText(str(values[i]))
            except Exception as e:
                pass

        container.get_value = get_list_value
        container.set_value = set_list_value

        # Set default values
        if config.default_value:
            container.set_value(config.default_value)

        return container

    @staticmethod
    def _create_multiple_checkbox(parent, config: FieldConfig):
        """Create multiple checkbox widget"""
        if not config.labels_list:
            raise ValueError("labels_list is required for multiple checkbox entry type")

        widget = MultipleCheckboxWidget(parent, config.labels_list, config.default_value or "")

        return widget

    @staticmethod
    def _create_grouped_checkbox(parent, config: FieldConfig):
        """Create grouped checkbox widget with sections and groups"""
        # Get structure from config (required for grouped_checkbox)
        structure = getattr(config, 'structure', None)
        if structure is None:
            raise ValueError("structure is required for grouped_checkbox entry type")

        widget = GroupedCheckboxWidget(
            parent,
            structure=structure,
            default_value=config.default_value or ""
        )

        return widget
